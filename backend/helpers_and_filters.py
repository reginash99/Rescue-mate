import argparse
import librosa
import torch
import os
import numpy as np
from scipy.signal import butter, sosfiltfilt
import subprocess
from models.stfts import mag_phase_stft, mag_phase_istft
import datetime 
import json 

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
def bandpass_filter(audio, lowcut=80.0, highcut=7000.0, fs=16000, order=6):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq

    sos = butter(order, [low, high], btype='bandpass', output='sos')
    filtered = sosfiltfilt(sos, audio)

    return filtered

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

def save_intermediate_transcript(script_base_name, stage_name, transcript, out_dir="output_transcriptions"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if stage_name=="final":
        fname = os.path.join(out_dir, f"{script_base_name}_{stage_name}_{timestamp}.json")
    else: 
        fname = os.path.join(out_dir, f"{script_base_name}_{stage_name}_{timestamp}_intermediate.json")
    
    os.makedirs(out_dir, exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

# Chunked SEMamba denoising for audio recordings longer than 4 minutes to keep peak GPU memory low while remaining relatively fast
def semamba_denoise_chunks(audio_np, sr, model, device, n_fft, hop_size, win_size, compress_factor,
                           chunk_size_sec=8.0, overlap_sec=2.0):
    
    model.eval()
    chunk_size = int(chunk_size_sec * sr)
    overlap = int(overlap_sec * sr)
    if chunk_size <= 0:
        raise ValueError("chunk_size_sec too small")
    step = chunk_size - overlap

    total_len = len(audio_np)
    n_steps = max(1, (total_len - overlap + step - 1) // step)
    padded_len = step * n_steps + overlap
    pad_amount = max(0, padded_len - total_len)
    audio = np.concatenate([audio_np, np.zeros(pad_amount, dtype=audio_np.dtype)])

    out = np.zeros_like(audio)
    win = np.hanning(chunk_size).astype(np.float32)
    norm = np.zeros_like(audio)

    for i in range(0, padded_len - overlap, step):
        chunk = audio[i:i+chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))

        noisy_wav = torch.from_numpy(chunk.astype(np.float32)).to(device)
        norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
        noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)

        with torch.no_grad():
            noisy_amp, noisy_pha, _ = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
            noisy_amp = noisy_amp.to(device).half()
            noisy_pha = noisy_pha.to(device).half()

            amp_g, pha_g, _ = model(noisy_amp, noisy_pha)

            try:
                del noisy_amp, noisy_pha
                torch.cuda.empty_cache()
                mamba_t = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor)
                mamba_chunk = mamba_t.squeeze().cpu().detach().numpy()
            
            except RuntimeError as e:
                print(f"GPU ISTFT failed with {e}; falling back to CPU ISTFT for this chunk")
                mamba_t = mag_phase_istft(amp_g.float().cpu(), pha_g.float().cpu(), n_fft, hop_size, win_size, compress_factor)
                mamba_chunk = mamba_t.squeeze().detach().numpy()

            try:
                del amp_g, pha_g
            except Exception:
                pass
            torch.cuda.empty_cache()

        mamba_chunk = (mamba_chunk / norm_factor.cpu().item())

        out[i:i+chunk_size] += mamba_chunk * win
        norm[i:i+chunk_size] += win

    norm[norm == 0] = 1.0
    out = out[:total_len] / norm[:total_len]
    out = out / (np.max(np.abs(out)) + 1e-9)
    
    return out
