import argparse
import librosa
import numpy as np
from scipy.signal import butter, sosfiltfilt
import subprocess

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

