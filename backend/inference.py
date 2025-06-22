import glob
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
import numpy as np
import scipy.signal as signal
from scipy.signal import butter, sosfiltfilt
import subprocess
import librosa
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import soundfile as sf
import concurrent.futures
#from deepfilter.filter import DeepFilterNet
import concurrent.futures
import glob
from whisper import DecodingOptions

from utils.util import (
    load_ckpts, load_optimizer_states, save_checkpoint,
    build_env, load_config, initialize_seed, 
    print_gpu_info, log_model_info, initialize_process_group,
)

#os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:16"

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

#Designed for: post-denoised but still unclear speech, Real-time capable (low CPU/GPU use),Runs as a CLI or via Python wrapper, Open-source + pretrained
def run_deepfilternet(input_folder, output_folder):
    subprocess.run(["deepFilter", "-i", input_folder, "-o", output_folder], check=True)


# A better DSP method than Wiener, it: Estimates noise from lowest-energy frames, Subtracts that from the spectrogram, Preserves speech formants better than Wiener, Works well on phone calls + radio
# def spectral_subtraction(audio, sampling_rate, n_fft=512, hop_length=128):
#     f, t, Zxx = signal.stft(audio, fs=sampling_rate, nperseg=n_fft, noverlap=n_fft - hop_length)
#     magnitude = np.abs(Zxx)
#     phase = np.angle(Zxx)

#     # Estimate noise as 10th percentile across time (adaptive)
#     noise_est = np.percentile(magnitude, 10, axis=1, keepdims=True)
#     clean_mag = np.maximum(magnitude - noise_est, 0)

#     cleaned_stft = clean_mag * np.exp(1j * phase)
#     _, enhanced_audio = signal.istft(cleaned_stft, fs=sampling_rate, nperseg=n_fft, noverlap=n_fft - hop_length)

#     return enhanced_audio


def inference(args, device):
    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    sampling_rate = cfg['stft_cfg']['sampling_rate']

    model = SEMamba(cfg).to(device).half()
    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)

    model.eval()
    
    #load the whisper model 
    whisper_model = whisper.load_model("small", device="cpu")
    #whisper_model = whisper_model.to(device)

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
        for i, fname in enumerate(os.listdir( args.input_folder )):
            print(fname, args.input_folder)
            files = os.listdir(args.input_folder)
        
        def process_file(fname):
            # 1) load + resample once
            wav, sr = librosa.load(os.path.join(args.input_folder, fname), sr=16000, mono=True)
            wav = wav / np.max(np.abs(wav))

            # 2) light bandpass *before* heavy model
            wav = bandpass_filter(wav, lowcut=200.0, highcut=4000.0, fs=16000, order=6)
            wav = np.ascontiguousarray(wav)

            # 3) chunk into 10 s pieces and denoise each
            max_samples = 16000 * 3
            chunks = [wav[i:i+max_samples] for i in range(0, len(wav), max_samples)]
            clean_chunks = []
            
            for chunk in chunks:
                # move data to GPU in half precision for the model
                x_fp16 = torch.from_numpy(chunk).to(device).unsqueeze(0).half()

                # 1) STFT in float32 so cuFFT accepts your 400-sample frame
                A_fp32, P_fp32, _ = mag_phase_stft(
                    x_fp16.float(), n_fft, hop_size, win_size, compress_factor
                )
                # cast the spectrogram back to half for SEMamba
                A_fp16, P_fp16 = A_fp32.half(), P_fp32.half()

                # 2) run the SEMamba model in FP16
                Ag_fp16, Pg_fp16, _ = model(A_fp16, P_fp16)

                # 3) ISTFT in float32 as well, to avoid the same half-precision FFT issue
                out_fp32 = mag_phase_istft(
                    Ag_fp16.float(), Pg_fp16.float(), n_fft, hop_size, win_size, compress_factor
                )

                # collect the cleaned audio chunk (always in CPU float32 NumPy)
                clean_chunks.append(out_fp32.squeeze().cpu().detach().numpy())

            audio_np = np.concatenate(clean_chunks)
            
            # 5) optional post-clean DSP
            #audio_np = audio_clean.squeeze().detach().cpu().numpy()
            if args.post_processing_PCS:
                audio_np = cal_pcs(audio_np)

            ## 7) write the SEMamba-cleaned WAV
            semamba_out = os.path.join(args.output_folder, fname)
            sf.write(semamba_out, audio_np, 16000, 'PCM_16')
            
            # free any stranded tensors
            torch.cuda.empty_cache()
            return semamba_out

        # run up to 2 files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as exe:
            cleaned_paths=list(exe.map(process_file, files))
        
        for semamba_out in cleaned_paths:
            base = os.path.splitext(os.path.basename(semamba_out))[0]
            dfn_dir = "dfn_output"
            os.makedirs(dfn_dir, exist_ok=True)
            run_deepfilternet(semamba_out, dfn_dir)

            pattern = os.path.join(dfn_dir, f"{base}*_DeepFilterNet3*.wav")
            matches = glob.glob(pattern)
            if not matches:
                raise FileNotFoundError(f"No DeepFilterNet3 output for {semamba_out}")
            dfn_file = matches[0]

            # 9) transcribe the DeepFilterNet3 output
            print(f"Transcribing cleaned file {os.path.basename(dfn_file)}…")
            result = whisper_model.transcribe(dfn_file, language='de', task='transcribe', no_speech_threshold=0.1, beam_size=5, temperature=0.0)


            print(f"Transcription for {fname}: {result['text']}")

            # 10) save the JSON
            out_json = os.path.join("output_transcriptions", f"{base}.json")
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

