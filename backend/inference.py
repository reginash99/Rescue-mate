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
def bandpass_filter(audio, lowcut=200.0, highcut=4000.0, fs=16000, order=6):
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


def estimate_snr(audio, frame_length=2048, hop_length=512, threshold=0.01):
    # Calculate short-term energy
    energies = [
        np.sum(audio[i:i+frame_length]**2)
        for i in range(0, len(audio)-frame_length, hop_length)
    ]
    energies = np.array(energies)
    # Assume lowest 10% energy frames are noise
    noise_energy = np.percentile(energies, 10)
    # Assume highest 10% are signal
    signal_energy = np.percentile(energies, 90)
    if noise_energy == 0:
        return float('inf')
    snr_db = 10 * np.log10(signal_energy / noise_energy)
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
            
            audio_np = bandpass_filter(audio_np, lowcut=200.0, highcut=4000.0, fs=16000, order=6)
            
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
            run_deepfilternet(results_out_path, args.output_folder)

            # transcribe the DeepFilterNet3 output
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

