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
from utils.util import load_config
import datetime
import webrtcvad
from collections import Counter

h = None
device = None 


# ------------------------------
# Helpers & Filters
# ------------------------------

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


# ------------------------------
# SNR estimation helpers
# ------------------------------


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

#using a VAD (voice activity detector) to separate speech and noise (for best results, but more complex)
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

#Decide if audio is clean, moderate, noisy, or muffled using SNR + spectral cues.
def classify_audio_quality(audio, sr=16000, snr_clean_thr=30, snr_light_thr=15, flatness_thr=0.08, hf_ratio_thr=0.05):
    """Decide if audio is clean, moderate, or noisy using SNR + spectral flatness."""
    
    snr_db = estimate_snr(audio)
    S = np.abs(librosa.stft(audio))
    flatness = librosa.feature.spectral_flatness(S=S).mean()

    fft = np.abs(np.fft.rfft(audio))**2
    freqs = np.fft.rfftfreq(len(audio), 1/sr)
    hf_energy = fft[(freqs > 3000) & (freqs < 8000)].sum()
    lf_energy = fft[freqs <= 3000].sum()
    hf_ratio = hf_energy / (lf_energy + 1e-9)

    # Extra: background RMS check
    rms = np.sqrt(np.mean(audio**2))
    rms_db = 20 * np.log10(rms + 1e-9)

    print(f"[AUDIO METRICS] SNR={snr_db:.2f} dB, flatness={flatness:.4f}, HF ratio={hf_ratio:.4f}, RMS={rms_db:.1f} dBFS")

    #If background RMS is high (noisy recording), force noisy/moderate
    if rms_db > -35 and snr_db < 35:
        return "noisy", snr_db, flatness, hf_ratio

    if snr_db < snr_light_thr:
        return "noisy", snr_db, flatness, hf_ratio
    elif hf_ratio < hf_ratio_thr or flatness < flatness_thr:
        return "muffled", snr_db, flatness, hf_ratio
    elif snr_db < snr_clean_thr:
        return "moderate", snr_db, flatness, hf_ratio
    else:
        return "clean", snr_db, flatness, hf_ratio

# ------------------------------
# Transcript comparison logic
# ------------------------------

#Return a penalty if text is highly repetitive
def repetition_score(text: str, max_ngram=4) -> float:
    words = text.strip().split()
    if len(words) < 4:
        return 0.0

    score = 0.0

    # --- 1. Consecutive repetition ---
    count = 1
    for i in range(1, len(words)):
        if words[i] == words[i-1]:
            count += 1
            if count > 2:
                score += 1.0 * (count-2)   # heavy penalty per extra repeat
        else:
            count = 1

    # --- 2. N-gram repetition ---
    for n in range(2, max_ngram+1):
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]
        counts = Counter(ngrams)
        for ng, c in counts.items():
            if c > 2:
                score += (c-2) * n  # longer n-grams penalized harder

    return score


# Scoring function to compare transcripts after every filter and pick the best one
def score_transcript(result, baseline_len=None):
    segs = result.get("segments", [])
    avg_logprob = float(np.mean([s.get("avg_logprob", -10.0) for s in segs])) if segs else result.get("avg_logprob", -10.0)
    compression_ratio = result.get("compression_ratio", 1.0)
    text = result.get("text", "").strip()

    # Base score
    score = avg_logprob - 0.3 * compression_ratio

    # Too short penalty
    if baseline_len and len(text.split()) < 0.5 * baseline_len:
        score -= 1.0

    # Repetition penalty (stronger now)
    rep_penalty = repetition_score(text)
    score -= rep_penalty * 2.0   # multiply for stronger effect

    # Compression-ratio hard rejection
    if compression_ratio < 0.25:
        score -= 5.0   # very heavy penalty

    return score


def compare_and_update(old_result, new_result, stage_name):
    if old_result is None:
        return new_result

    baseline_len = len(old_result.get("text", "").split())
    old_score = score_transcript(old_result, baseline_len)
    new_score = score_transcript(new_result, baseline_len)

    print(f"[COMPARE] {stage_name}: old={old_score:.3f}, new={new_score:.3f}")

    if new_score > old_score:
        print("New transcript is better, replacing old one.")
        return new_result
    else:
        print("Old transcript is better, keeping it.")
        return old_result


def cleanup_repetition(text, max_repeat=3):
    words = text.split()
    cleaned = []
    count = 1
    for i, w in enumerate(words):
        if i > 0 and w == words[i-1]:
            count += 1
            if count > max_repeat:
                continue
        else:
            count = 1
        cleaned.append(w)
    return " ".join(cleaned)


# ------------------------------
# Whisper config
# ------------------------------


DOMAIN_PROMPT = (
    "Transkribiere Funkverkehr und Telefongespräche im Einsatzkontext. Verwende Funkrufnamen, Einsatzbegriffe und Abkürzungen korrekt. Zahlen immer als Ziffern wiedergeben (z. B. 35 statt fünfunddreißig). Keine Wörter erfinden, unklare Stellen mit '...' kennzeichnen. Behalte den typischen Funkstil: kurze Sätze, Telegrammstil, keine ausgeschmückte Grammatik."

)

def whisper_decode(model, audio_array, language=None):
    """Whisper inference with tuned params for radio speech."""
    
     #ensure no negative strides by copying
    if not isinstance(audio_array, np.ndarray):
        audio_array = np.array(audio_array)
    audio_array = np.ascontiguousarray(audio_array).astype(np.float32)

    return model.transcribe(
        audio_array,
        task="transcribe",
        language=language,
        condition_on_previous_text=False,   # Prevents bad carry-over across bursts
        initial_prompt=DOMAIN_PROMPT,       # Injects domain lexicon
        beam_size=8,                        # Better than greedy
        best_of=3,
        temperature=(0.2, 0.4),             # Deterministic + light fallback
        no_speech_threshold=0.1,
        word_timestamps=True
    )


# ------------------------------
# Core pipeline
# ------------------------------


def inference(args, device):
    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    
    #model = SEMamba(cfg).to(device).half()
    model = SEMamba(cfg).to(device)

    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)

    model.eval()
    
    #load the whisper model 
    whisper_model = whisper.load_model("small", device=device)
    #whisper_model = WhisperModel("small", device="cpu")

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

        full_path = os.path.join(args.input_folder, latest_fname)
        if not os.path.isfile(full_path):
            raise ValueError(f"{full_path} is not a valid file!")

        audio, sr = librosa.load(full_path, sr=None, mono=True)
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / (peak + 1e-9)

        base = os.path.splitext(latest_fname)[0]
        final_wav_out = os.path.join(args.output_folder, f"{base}_final.wav")
        best_result, best_audio = None, audio
        stage = "raw"


        # ===== Stage 1: RAW/Clean (always baseline) =====
        best_result = whisper_decode(whisper_model, best_audio)
        print(f"Stage RAW text: {best_result.get('text','').strip()}")
        
        quality, snr_db, flatness,hf_ratio = classify_audio_quality(best_audio, sr=sr)

        if quality == "clean":
            print("Audio classified as clean -> skipping filtering.")

        # ===== Stage 2: Band-pass (conditional) =====
        elif quality == "moderate":
            print("Audio is moderately noisy, applying bandpass.")
            bp_audio = bandpass_filter(best_audio)
            bp_result = whisper_decode(whisper_model, bp_audio)
            best_result = compare_and_update(best_result, bp_result, "band-pass")
            best_audio = bp_audio
        
         # ===== Stage 3: Band-pass + Pre-emphasis (conditional) =====
        elif quality == "muffled":
            print("Audio is muffled , applying bandpass and pre-emphasis.")
            bp_audio = bandpass_filter(best_audio)
            pe_audio = pre_emphasis(bp_audio)
            pe_result = whisper_decode(whisper_model, pe_audio)
            best_result = compare_and_update(best_result, pe_result, "band-pass+PE")
            best_audio = pe_audio

        # ===== Stage 4: SEMamba + Pre-emphasis +PE if needed (conditional) =====
        elif quality == "noisy":  #run SEMamba only when noisy enough
            print("Audio is noisy/muffled, applying SEmamba and bandpass.")
            noisy_wav = torch.FloatTensor(best_audio).to(device)
            norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
            
            noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
            noisy_amp, noisy_pha, _ = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
            
            #noisy_amp = noisy_amp.to(device).half()
            #noisy_pha = noisy_pha.to(device).half()

            noisy_amp = noisy_amp.to(device)
            noisy_pha = noisy_pha.to(device)

            amp_g, pha_g, _ = model(noisy_amp, noisy_pha)
            mamba_audio = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor)
            #mamba_audio = (mamba_audio / norm_factor).squeeze().cpu().detach().numpy()
            
            mamba_audio = mamba_audio.squeeze().cpu().detach().numpy()

            torch.cuda.empty_cache()

            # --- Always bandpass after SEMamba ---
            mamba_audio = bandpass_filter(mamba_audio, 200, 5000)

            # --- Conditional pre-emphasis ---
            fft = np.abs(np.fft.rfft(mamba_audio))**2
            freqs = np.fft.rfftfreq(len(mamba_audio), 1/sr)
            hf_energy = fft[(freqs > 3000) & (freqs < 8000)].sum()
            lf_energy = fft[freqs <= 3000].sum()
            hf_ratio = hf_energy / (lf_energy + 1e-9)

            stage_name = "SEMamba+BP"
            if hf_ratio < 0.05:
                print("Post-Mamba audio still muffled -> applying pre-emphasis.")
                mamba_audio = pre_emphasis(mamba_audio)
                stage_name += "+PE"

            if args.post_processing_PCS:
                mamba_audio = cal_pcs(mamba_audio)
        
            mamba_result = whisper_decode(whisper_model, mamba_audio)
            best_result = compare_and_update(best_result, mamba_result, stage_name)
            best_audio = mamba_audio


            # # ===== Stage 5: SEMamba + PE + Band-pass (conditional) =====
            # flatness = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(mamba_audio))).mean()
            # if flatness < 20:
            #     print("Audio is still noisy, applying bandpass after having run Mamba and pre-emphasis.")
            #     mbp_audio = bandpass_filter(best_audio)
            #     mbp_result = whisper_decode(whisper_model, mbp_audio)
            #     best_result = compare_and_update(best_result, mbp_result, "SEMamba+PE+BP")
            #     best_audio = mbp_audio

            # ===== Stage 5: DeepFilterNet (conditional) =====
            snr_post = estimate_snr_vad(best_audio, sr=16000)
            flatness_post = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(best_audio))).mean()
            if snr_post < 15 and flatness_post < 0.01:
                print(f"SNR Post={snr_post:.2f} dB, flatness post={flatness_post:.4f}")
                print("Audio is still noisy, applying DeepFilterNet.")

                tmp_dir = "tmp"
                os.makedirs(tmp_dir, exist_ok=True)
                dfn_path = os.path.join(tmp_dir, f"{base}_dfn.wav")
                sf.write(dfn_path, best_audio, 16000, 'PCM_16')
                
                run_deepfilternet(dfn_path, tmp_dir)
                
                dfn_audio, _ = librosa.load(dfn_path, sr=16000, mono=True)
                dfn_result = whisper_decode(whisper_model, dfn_audio)
                best_result = compare_and_update(best_result, dfn_result, "DeepFilterNet")
                best_audio = dfn_audio
                os.remove(dfn_path)

        # Save final
        sf.write(final_wav_out, best_audio, 16000, 'PCM_16')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        best_result["timestamp"] = timestamp
        best_result["text"] = cleanup_repetition(best_result["text"])
        out_json = os.path.join("output_transcriptions", f"{base}_{timestamp}.json")
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(best_result, f, ensure_ascii=False, indent=2)

        print(f"\nFINAL TEXT   : {best_result.get('text','').strip()}")
        print(f"SAVED WAV    : {final_wav_out}")
        print(f"SAVED JSON   : {out_json}")


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

