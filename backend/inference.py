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
from scipy.signal import butter, lfilter

from utils.util import (
    load_ckpts, load_optimizer_states, save_checkpoint,
    build_env, load_config, initialize_seed, 
    print_gpu_info, log_model_info, initialize_process_group,
)

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


#A minimal bandpass filter to improve speech intelligibility (esp. for radio-style speech):
def bandpass_filter(audio, lowcut=300.0, highcut=3400.0, fs=16000, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, audio)


# Wiener filter is a classic, lightweight DSP method used in: Telephony, Hearing aids, Old ASR systems. It’s not as smart as NSNet2, but: Works on CPU, Requires no model, Boosts voice quality
def wiener_filter(audio, sampling_rate):
    """
    Apply a basic spectral Wiener filter to enhance speech.
    """
    # STFT
    f, t, Zxx = signal.stft(audio, fs=sampling_rate, nperseg=512)
    magnitude = np.abs(Zxx)
    phase = np.angle(Zxx)

    # Estimate noise as minimum energy across time
    noise_est = np.min(magnitude, axis=1, keepdims=True)

    # Wiener filter formula
    wiener_gain = np.maximum(1e-5, 1 - (noise_est**2 / (magnitude**2 + 1e-5)))

    # Apply gain
    enhanced_mag = magnitude * wiener_gain
    enhanced_stft = enhanced_mag * np.exp(1j * phase)

    # Inverse STFT
    _, enhanced_audio = signal.istft(enhanced_stft, fs=sampling_rate, nperseg=512)

    return enhanced_audio

def inference(args, device):
    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    sampling_rate = cfg['stft_cfg']['sampling_rate']

    model = SEMamba(cfg).to(device)
    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)

    model.eval()
    
    #load the whisper model 
    whisper_model = whisper.load_model("small", device=device)

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
            noisy_wav, _ = librosa.load(os.path.join( args.input_folder, fname ), sr=sampling_rate)
            noisy_wav = torch.FloatTensor(noisy_wav).to(device)

            norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
            noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
            noisy_amp, noisy_pha, noisy_com = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
            amp_g, pha_g, com_g = model(noisy_amp, noisy_pha)
            audio_g = mag_phase_istft(amp_g, pha_g, n_fft, hop_size, win_size, compress_factor)
            audio_g = audio_g / norm_factor

            # INSERT ADDITIONAL FILTERS AFTER THIS LINE (the line above: audio_g =...)

            # Convert audio to numpy and filter it
            audio_np = audio_g.squeeze().cpu().numpy()
            filtered_audio = bandpass_filter(audio_np, fs=sampling_rate)
            enhanced_audio = wiener_filter(filtered_audio, sampling_rate)

            output_file = os.path.join(args.output_folder, fname)

            if args.post_processing_PCS == True:
                #audio_g = cal_pcs(audio_g.squeeze().cpu().numpy())
                sf.write(output_file, enhanced_audio, sampling_rate, 'PCM_16')
            else:
                sf.write(output_file, enhanced_audio, sampling_rate, 'PCM_16')
            
            
            #Transcribe the audio using Whisper
            print(f"Transcribing {fname}...")
            result = whisper_model.transcribe(output_file, language='de', task='transcribe')
            print(f"Transcription for {fname}: {result['text']}")

            # Save transcription as JSON
            transcription_folder = "output_transcriptions"
            os.makedirs(transcription_folder, exist_ok=True)
            json_filename = os.path.splitext(fname)[0] + ".json"
            json_path = os.path.join(transcription_folder, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)


def main():
    print('Initializing Inference Process..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', default='test_sounds')
    parser.add_argument('--output_folder', default='results')
    parser.add_argument('--config', default='results')
    parser.add_argument('--checkpoint_file', required=True)
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

