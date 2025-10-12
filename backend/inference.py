# inference.py
import os
import argparse
import datetime
import numpy as np
import soundfile as sf
import librosa
import torch
import requests
import dotenv

from models.stfts import mag_phase_stft, mag_phase_istft
from models.generator import SEMamba
from models.pcs400 import cal_pcs
from utils.util import load_config
from snr_helpers import estimate_snr_vad, classify_audio_quality
from helpers_and_filters import bandpass_filter, pre_emphasis, run_deepfilternet, str2bool, semamba_denoise_chunks
from transcription_comparison import cleanup_repetition, compare_and_update
from db import insert_intermediate_record, set_success_status, add_audio_path
import whisper

dotenv.load_dotenv()

# ---------- API callbacks ----------
API_BASE = os.getenv("API_BASE_URL", "http://api:8000")  # docker service name by default

def send_log_to_frontend(current_id: int, message: str):
    try:
        r = requests.post(f"{API_BASE}/log-update", json={"id": current_id, "message": message}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print("Failed to send log:", e)

def notify_transcription_ready(current_id: int):
    try:
        r = requests.post(f"{API_BASE}/transcription-ready", json={"id": current_id}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print("Failed to notify API:", e)

# ---------- Whisper config ----------
DOMAIN_PROMPT = (
    "Der Input sind Funksprüche von Rettungseinsätzen in Hamburg. Alle hörbaren Wörter "
    "(einschließlich Orts- und Straßennamen) exakt wiedergeben. Keine zusätzlichen Wörter "
    "erfinden oder ergänzen. Zahlen als Ziffern darstellen. Unverständliche Stellen mit '...' "
    "markieren. Kurze Sätze, einfache Grammatik."
)

def whisper_decode(model, audio_array, language=None):
    if not isinstance(audio_array, np.ndarray):
        audio_array = np.array(audio_array)
    audio_array = np.ascontiguousarray(audio_array).astype(np.float32)
    return model.transcribe(
        audio_array,
        task="transcribe",
        language=language,
        condition_on_previous_text=False,
        initial_prompt=DOMAIN_PROMPT,
        beam_size=5,
        best_of=3,
        patience=1.2,
        temperature=(0.0, 0.2),
        no_speech_threshold=0.1,
        compression_ratio_threshold=2.4,
        word_timestamps=True,
    )

# ---------- Core pipeline ----------
def inference(args, device):
    current_id = int(args.current_id)

    cfg = load_config(args.config)
    n_fft = cfg['stft_cfg']['n_fft']
    hop_size = cfg['stft_cfg']['hop_size']
    win_size = cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']

    send_log_to_frontend(current_id, "Loading models…")

    model = SEMamba(cfg).to(device).half()
    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])
    model.eval()

    os.makedirs(args.output_folder, exist_ok=True)

    whisper_model = whisper.load_model("small", device=device)

    with torch.no_grad():
        # pick file
        if args.file is not None:
            latest_fname = args.file
        else:
            files = [f for f in os.listdir(args.input_folder) if f.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.m4a'))]
            if not files:
                raise ValueError("No audio files found in input_folder.")
            latest_file = max([os.path.join(args.input_folder, f) for f in files], key=os.path.getmtime)
            latest_fname = os.path.basename(latest_file)

        full_path = os.path.join(args.input_folder, latest_fname)
        if not os.path.isfile(full_path):
            raise ValueError(f"{full_path} is not a valid file!")

        # load & normalize
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

        # ===== Stage 1: RAW =====
        send_log_to_frontend(current_id, "Transcribing (RAW)…")
        best_result = whisper_decode(whisper_model, best_audio)
        best_result["text"] = cleanup_repetition(best_result["text"])
        insert_intermediate_record(best_result["text"].strip(), 1, current_id)
        if best_result["text"]:
            set_success_status(current_id, True)

        # Unblock API response
        notify_transcription_ready(current_id)

        # Quality & branching
        quality, snr_db, flatness, hf_ratio = classify_audio_quality(best_audio, sr=sr)
        send_log_to_frontend(current_id, f"Audio quality: {quality} (SNR≈{snr_db:.1f} dB)")

        if quality == "clean":
            send_log_to_frontend(current_id, "Clean → skipping filters.")

        elif quality == "moderate":
            send_log_to_frontend(current_id, "Moderate noise → band-pass…")
            bp_audio = bandpass_filter(best_audio)
            bp_result = whisper_decode(whisper_model, bp_audio)
            best_result, verdict = compare_and_update(best_result, bp_result, "bandpass")
            best_audio = bp_audio
            insert_intermediate_record(bp_result["text"].strip(), 6, current_id)
            _log_verdict(current_id, verdict)

        elif quality == "muffled":
            send_log_to_frontend(current_id, "Muffled → band-pass + pre-emphasis…")
            bp_audio = bandpass_filter(best_audio)
            pe_audio = pre_emphasis(bp_audio)
            pe_result = whisper_decode(whisper_model, pe_audio)
            best_result, verdict = compare_and_update(best_result, pe_result, "bandpass+PE")
            best_audio = pe_audio
            insert_intermediate_record(pe_result["text"].strip(), 2, current_id)
            _log_verdict(current_id, verdict)

        elif quality == "noisy":
            send_log_to_frontend(current_id, "Noisy → SEMamba + band-pass…")

            clip_seconds = len(best_audio) / float(sr)
            if clip_seconds > 4 * 60:
                mamba_audio = semamba_denoise_chunks(
                    best_audio, sr, model, device, n_fft, hop_size, win_size,
                    compress_factor=0.8, chunk_size_sec=8.0, overlap_sec=2.0
                )
            else:
                noisy_wav = torch.FloatTensor(best_audio).to(device)
                norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
                noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
                noisy_amp, noisy_pha, _ = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor=0.8)
                noisy_amp = noisy_amp.to(device).half()
                noisy_pha = noisy_pha.to(device).half()

                amp_g, pha_g, _ = model(noisy_amp, noisy_pha)
                mamba_audio = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor=0.8)
                mamba_audio = (mamba_audio / norm_factor.cpu().item()).squeeze().cpu().detach().numpy()
                mamba_audio = mamba_audio / (np.max(np.abs(mamba_audio)) + 1e-9)

                del amp_g, pha_g, noisy_amp, noisy_pha
                torch.cuda.empty_cache()

            mamba_audio = bandpass_filter(mamba_audio, 80, 7000)

            # decide PE
            fft = np.abs(np.fft.rfft(mamba_audio)) ** 2
            freqs = np.fft.rfftfreq(len(mamba_audio), 1 / sr)
            hf_energy = fft[(freqs > 3000) & (freqs < 8000)].sum()
            lf_energy = fft[freqs <= 3000].sum()
            hf_ratio2 = hf_energy / (lf_energy + 1e-9)

            if args.post_processing_PCS:
                mamba_audio = cal_pcs(mamba_audio)

            mamba_result = whisper_decode(whisper_model, mamba_audio)
            best_result, verdict = compare_and_update(best_result, mamba_result, "SEMamba+BP")
            best_audio = mamba_audio
            insert_intermediate_record(mamba_result["text"].strip(), 3, current_id)
            _log_verdict(current_id, verdict)

            if hf_ratio2 < 0.02:
                send_log_to_frontend(current_id, "Still muffled → pre-emphasis after SEMamba…")
                mamba_audio = pre_emphasis(mamba_audio)
                mamba_pe_result = whisper_decode(whisper_model, mamba_audio)
                best_result, verdict = compare_and_update(best_result, mamba_pe_result, "SEMamba+BP+PE")
                best_audio = mamba_audio
                insert_intermediate_record(mamba_pe_result["text"].strip(), 4, current_id)
                _log_verdict(current_id, verdict)

            # DeepFilterNet if still bad
            snr_post = estimate_snr_vad(best_audio, sr=16000)
            flatness_post = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(best_audio))).mean()
            if snr_post < 15 and flatness_post < 0.01:
                send_log_to_frontend(current_id, "Still noisy → DeepFilterNet…")
                tmp_dir = "tmp"
                os.makedirs(tmp_dir, exist_ok=True)
                dfn_path = os.path.join(tmp_dir, f"{base}_dfn.wav")
                sf.write(dfn_path, best_audio, 16000, 'PCM_16')

                run_deepfilternet(dfn_path, tmp_dir)

                dfn_audio, _ = librosa.load(dfn_path, sr=16000, mono=True)
                dfn_result = whisper_decode(whisper_model, dfn_audio)
                best_result, verdict = compare_and_update(best_result, dfn_result, "DeepFilterNet")
                best_audio = dfn_audio
                insert_intermediate_record(dfn_result["text"].strip(), 5, current_id)
                _log_verdict(current_id, verdict)

                try:
                    os.remove(dfn_path)
                except Exception:
                    pass

        # ------- Save final outputs -------
        sf.write(final_wav_out, best_audio, 16000, 'PCM_16')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        best_result["timestamp"] = timestamp
        best_result["text"] = cleanup_repetition(best_result["text"])

        add_audio_path(current_id, final_wav_out, 1)  # 1 = output audio
        insert_intermediate_record(best_result["text"].strip(), 0, current_id)

        print(f"\nFINAL TEXT   : {best_result.get('text','').strip()}")
        print(f"SAVED WAV    : {final_wav_out}")
        print(f"BASE NAME    : {base}")
        send_log_to_frontend(current_id, "Finished. Final audio + text saved.")

def _log_verdict(current_id: int, verdict: str):
    if verdict == "new is nonsense":
        send_log_to_frontend(current_id, "New transcription looks wrong → keeping previous.")
    elif verdict == "new":
        send_log_to_frontend(current_id, "New transcription chosen.")
    else:
        send_log_to_frontend(current_id, "Previous transcription kept.")

# ---------- CLI ----------
def main():
    print('Initializing Inference Process..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', default='test_sounds')
    parser.add_argument('--output_folder', default='results')
    parser.add_argument('--config', required=True)                 # was wrongly 'results'
    parser.add_argument('--checkpoint_file', required=True)
    parser.add_argument('--post_processing_PCS', type=str2bool, default=False)
    parser.add_argument('--file', type=str, default=None, help='Specific file to process')
    parser.add_argument('--current_id', type=int, required=True, help='Current ID for database record')
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("Currently, CPU mode is not supported.")

    device = torch.device('cuda')
    inference(args, device)

if __name__ == '__main__':
    main()
