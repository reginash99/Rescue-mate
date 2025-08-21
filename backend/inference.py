import os
import argparse
import json
import torch
import librosa
from models.stfts import mag_phase_stft, mag_phase_istft
from models.generator import SEMamba
from models.pcs400 import cal_pcs
import soundfile as sf
import whisper
# from faster_whisper import WhisperModel
import numpy as np
import scipy.signal as signal
from scipy.signal import butter, sosfiltfilt
import subprocess
import librosa
import soundfile as sf
from utils.util import load_config
import datetime
import webrtcvad

h = None
device = None 

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


#A bandpass filter to improve speech intelligibility (esp. for radio-style speech):
def bandpass_filter(audio, lowcut=200.0, highcut=5000.0, fs=16000, order=6):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq

    sos = butter(order, [low, high], btype='bandpass', output='sos')
    filtered = sosfiltfilt(sos, audio)

    return filtered


# has not been used in the current code, but can be useful for enhancing consonants
# To further enhance consonants that Whisper needs (like "s", "t", "sh"), use it after bandpass
def pre_emphasis(audio, coeff=0.97):
    return np.append(audio[0], audio[1:] - coeff * audio[:-1])


#Designed for: post-denoised but still unclear speech, Real-time capable (low CPU/GPU use),Runs as a CLI or via Python wrapper, Open-source + pretrained.
def run_deepfilternet(input_folder, output_folder):
    subprocess.run(["deepFilter", "-i", input_folder, "-o", output_folder], check=True)

def is_muffled(audio, sr=16000, threshold=0.2):
    S = np.abs(librosa.stft(audio))
    flatness = librosa.feature.spectral_flatness(S=S).mean()
    return flatness < threshold

#signal-to-noise ratio estimation to determine if audio is clean enough
def estimate_snr(audio, frame_length=2048, hop_length=512):
    # Calculate short-term energy
    energies = np.array([
        np.sum(audio[i:i+frame_length]**2)
        for i in range(0, len(audio)-frame_length, hop_length)
    ])
    n = len(energies)
    if n < 10:
        return 0  # Not enough data

    # Use lowest 10% as noise, highest 10% as signal
    n10 = max(1, int(0.1 * n))
    sorted_indices = np.argsort(energies)
    noise_indices = sorted_indices[:n10]
    signal_indices = sorted_indices[-n10:]

    noise_samples = np.concatenate([
        audio[i*hop_length:i*hop_length+frame_length] for i in noise_indices
    ])
    signal_samples = np.concatenate([
        audio[i*hop_length:i*hop_length+frame_length] for i in signal_indices
    ])

    noise_power = np.mean(noise_samples**2)
    signal_power = np.mean(signal_samples**2)
    if noise_power == 0:
        return float('inf')
    snr_db = 10 * np.log10(signal_power / noise_power)
    return snr_db

#use a VAD (voice activity detector) to separate speech and noise (for best results, but more complex)
def estimate_snr_vad(audio, sr=16000, frame_ms=30):
    # Convert to 16-bit PCM for VAD
    audio_pcm = (audio * 32767).astype(np.int16)
    vad = webrtcvad.Vad(2)  # 0-3, 3=most aggressive

    frame_len = int(sr * frame_ms / 1000)
    n_frames = len(audio_pcm) // frame_len

    speech_frames = []
    noise_frames = []

    for i in range(n_frames):
        start = i * frame_len
        stop = start + frame_len
        frame = audio_pcm[start:stop]
        if len(frame) < frame_len:
            continue
        is_speech = vad.is_speech(frame.tobytes(), sr)
        if is_speech:
            speech_frames.append(frame)
        else:
            noise_frames.append(frame)

    if not noise_frames or not speech_frames:
        # fallback to energy-based if VAD fails
        return estimate_snr(audio)

    noise = np.concatenate(noise_frames)
    speech = np.concatenate(speech_frames)
    noise_power = np.mean(noise.astype(np.float32)**2)
    speech_power = np.mean(speech.astype(np.float32)**2)
    if noise_power == 0:
        return float('inf')
    snr_db = 10 * np.log10(speech_power / noise_power)
    return snr_db



def inference(args, device):
    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    
    model = SEMamba(cfg).to(device).half()
    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)

    model.eval()
    
    #load the whisper model 
    whisper_model = whisper.load_model("small", device=device)
    #whisper_model = WhisperModel("small", device="cpu")
    apply_bandpass = True
    apply_deepfilternet = True

    with torch.no_grad():
        # You can use data.json instead of input_folder with:
        # ---------------------------------------------------- #
        # with open("data/test_noisy.json", 'r') as json_file:
        #     test_files = json.load(json_file)
        # for i, fname in enumerate( test_files ): 
        #     folder_path = os.path.dirname(fname)
        #     fname = os.path.basename(fname)
        #     noisy_wav, _ = librosa.load(os.path.join( folder_path, fname ), sr=sampling_rate)
        #     noisy_wav = torch.FloatTensor(noisy_wav).to(device)
        # ---------------------------------------------------- #

        if args.file is not None:
            latest_fname = args.file
            print(f"Processing specified file: {latest_fname}")
        else:
            files = os.listdir(args.input_folder)
            latest_file = max([os.path.join(args.input_folder, f) for f in files if f.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.m4a'))], key=os.path.getmtime)
            latest_fname = os.path.basename(latest_file)
            print(f"Processing latest file: {latest_fname}")

        
        def process_file(fname):
            
            full_path = os.path.join(args.input_folder, fname)
            if not os.path.isfile(full_path):
                raise ValueError(f"{full_path} is not a valid file!")

            noisy_wav, sr = librosa.load(os.path.join(args.input_folder, fname), sr=None, mono=True)

            if sr != 16000:
                noisy_wav = librosa.resample(noisy_wav, orig_sr=sr, target_sr=16000)
                sr = 16000
            
            if np.max(np.abs(noisy_wav)) > 0:
                noisy_wav = noisy_wav / np.max(np.abs(noisy_wav))


            # Estimate SNR
            snr_db = estimate_snr_vad(noisy_wav, sr=sr)
            print(f"SNR for {fname}: {snr_db:.2f} dB")

             # Decide if audio is clean
            CLEAN_SNR_THRESHOLD = 15 #Adjust this value as needed
            LIGHT_DENOISE_THRESHOLD = 11  # optional

            if snr_db > CLEAN_SNR_THRESHOLD and not is_muffled(noisy_wav, sr=sr):
                print("Audio is clean, skipping denoising steps.")
                return noisy_wav
            
            elif snr_db > LIGHT_DENOISE_THRESHOLD and not is_muffled(noisy_wav, sr=sr):
                print("Audio is moderately noisy, applying only bandpass.")
                audio_np = bandpass_filter(noisy_wav, lowcut=200.0, highcut=5000, fs=16000, order=6)
                return audio_np

            else:
            # --- Denoising pipeline below ---
                print("Audio is  noisy, applying denoising steps.")
                noisy_wav = torch.FloatTensor(noisy_wav).to(device)
                norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
                
                noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
                noisy_amp, noisy_pha, noisy_com = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
                
                noisy_amp = noisy_amp.to(device).half()
                noisy_pha = noisy_pha.to(device).half()

                amp_g, pha_g, com_g = model(noisy_amp, noisy_pha)
                
                audio_g = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor)
                
                audio_g = audio_g / norm_factor
                
                # free any stranded tensors
                torch.cuda.empty_cache()
                
                audio_np = audio_g.squeeze().cpu().detach().numpy()


                FLATNESS_THRESHOLD = 0.01
                flatness = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(audio_np))).mean()
                if snr_db > CLEAN_SNR_THRESHOLD and flatness > FLATNESS_THRESHOLD:
                    print("Speech is clear after Mamba, skipping bandpass.")
                else:
                    print("Speech still not clear, applying bandpass.")
                    audio_np = bandpass_filter(audio_np, lowcut=200.0, highcut=5000.0, fs=16000, order=6)
                
                #optional post-clean DSP
                if args.post_processing_PCS:
                    audio_np = cal_pcs(audio_np)

                return audio_np

        cleaned_paths = [process_file(latest_fname)]

        for i, audio_np in enumerate(cleaned_paths):
            fname = latest_fname 
            base = os.path.splitext(os.path.basename(fname))[0]            
            results_out_path = os.path.join(args.output_folder, f"{base}_final.wav")

            sf.write(results_out_path, audio_np, 16000, 'PCM_16')
            
            #check if DeepFilterNet3 is needed
            CLEAN_SNR_THRESHOLD = 15
            FLATNESS_THRESHOLD = 0.01
            
            audio_for_check, sr_check = librosa.load(results_out_path, sr=16000, mono=True)
            snr_post = estimate_snr_vad(audio_for_check, sr=sr_check)
            flatness_post = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(audio_for_check))).mean()
            
            print(f"Post-processing SNR: {snr_post:.2f} dB, Flatness: {flatness_post:.2f}")

            if snr_post > CLEAN_SNR_THRESHOLD and flatness_post > FLATNESS_THRESHOLD:
                print("Speech is clear after Mamba+bandpass, skipping DeepFilterNet.")
            else:
                print("Speech still not clear, applying DeepFilterNet.")
                run_deepfilternet(results_out_path, args.output_folder)


            # transcribe the output
            print(f"Transcribing cleaned file {os.path.basename(results_out_path)}…")
            result = whisper_model.transcribe(results_out_path, task='transcribe', no_speech_threshold=0.1, beam_size=5, temperature=0.0)
            #segments,_ = whisper_model.transcribe(results_out_path, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))

            # result=""
            # for segment in segments:
            #     result+=segment.text
            
            #print(f"Transcription for {fname}: {result}")
            print(f"Transcription for {fname}: {result['text']}")

            # save the JSON
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            result["timestamp"] = timestamp
            out_json = os.path.join("output_transcriptions", f"{base}_{timestamp}.json")
            os.makedirs(os.path.dirname(out_json), exist_ok=True)
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)


def main():
    print('Initializing Inference Process..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', default='test_sounds')
    parser.add_argument('--output_folder', default='results')
    parser.add_argument('--config', default='results')
    parser.add_argument('--checkpoint_file', required=True)
    #parser.add_argument('--whisper_dir',required=True,help="path to your fine-tuned Whisper folder (where you ran trainer.save_model)")
    parser.add_argument('--post_processing_PCS', type=str2bool, default=False)
    parser.add_argument('--file', type=str, default=None, help='Specific file to process')
    args = parser.parse_args()

    global device
    if torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        #device = torch.device('cpu')
        raise RuntimeError("Currently, CPU mode is not supported.")
        

    inference(args, device)


if __name__ == '__main__':
    main()

