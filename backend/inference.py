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
from utils.util import load_config
import datetime
from collections import Counter
from snr_helpers import estimate_snr_vad, classify_audio_quality
from helpers_and_filters import bandpass_filter, pre_emphasis, run_deepfilternet, str2bool
from transcription_comparison import cleanup_repetition, compare_and_update

h = None
device = None 

# ------------------------------
# Whisper config
# ------------------------------

DOMAIN_PROMPT = (
    "Der Input sind Funksprüche von Rettungseinsätzen in Hamburg. Alle hörbaren Wörter (einschließlich Orts- und Straßennamen) exakt wiedergeben. Keine zusätzlichen Wörter erfinden oder ergänzen. Zahlen als Ziffern darstellen. Unverständliche Stellen mit '...' markieren. Kurze Sätze, einfache Grammatik."
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
        condition_on_previous_text=False,   
        initial_prompt=DOMAIN_PROMPT,       # Injects domain lexicon
        beam_size=5,                        
        best_of=3,
        patience=1.2,
        temperature=(0.0, 0.2),             
        no_speech_threshold=0.1,
        compression_ratio_threshold=2.4,
        word_timestamps=True
    )


# Chunked SEMamba denoising to keep peak GPU memory low while remaining fast.
def semamba_denoise_chunks(audio_np, sr, model, device, n_fft, hop_size, win_size, compress_factor,
                           chunk_size_sec=8.0, overlap_sec=2.0):
    
    model.eval()
    chunk_size = int(chunk_size_sec * sr)
    overlap = int(overlap_sec * sr)
    if chunk_size <= 0:
        raise ValueError("chunk_size_sec too small")
    step = chunk_size - overlap

    total_len = len(audio_np)
    # pad to fit last chunk
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

        # Prepare tensor on device
        noisy_wav = torch.from_numpy(chunk.astype(np.float32)).to(device)
        # normalize per-chunk (keeps numerical stability)
        norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
        noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)

        with torch.no_grad():
            noisy_amp, noisy_pha, _ = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
            noisy_amp = noisy_amp.to(device).half()
            noisy_pha = noisy_pha.to(device).half()

            amp_g, pha_g, _ = model(noisy_amp, noisy_pha)

            # Try fast GPU ISTFT after freeing inputs
            try:
                del noisy_amp, noisy_pha
                torch.cuda.empty_cache()
                mamba_t = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor)
                mamba_chunk = mamba_t.squeeze().cpu().detach().numpy()
            
            except RuntimeError as e:
                # Fallback to CPU ISTFT if OOM
                print(f"GPU ISTFT failed with {e}; falling back to CPU ISTFT for this chunk")
                mamba_t = mag_phase_istft(amp_g.float().cpu(), pha_g.float().cpu(), n_fft, hop_size, win_size, compress_factor)
                mamba_chunk = mamba_t.squeeze().detach().numpy()

            # cleanup
            try:
                del amp_g, pha_g
            except Exception:
                pass
            torch.cuda.empty_cache()

        # undo per-chunk normalization
        mamba_chunk = (mamba_chunk / norm_factor.cpu().item())

        # apply window and overlap-add
        out[i:i+chunk_size] += mamba_chunk * win
        norm[i:i+chunk_size] += win

    norm[norm == 0] = 1.0
    out = out[:total_len] / norm[:total_len]
    out = out / (np.max(np.abs(out)) + 1e-9)
    
    return out


# ------------------------------
# Core pipeline
# ------------------------------

def inference(args, device):
    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    
    model = SEMamba(cfg).to(device).half()
    #model = SEMamba(cfg).to(device)

    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)

    model.eval()
    
    whisper_model = whisper.load_model("small", device=device)

    with torch.no_grad():
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
        #FIRST RAW TRANSCRIPT IS GENERATED HERE and saved at best_result - NO FILTERS APPLIED
        best_result = whisper_decode(whisper_model, best_audio)
        print(f"Stage RAW text: {best_result.get('text','').strip()}")
        #Here is where this transcription will be saved to the backend as the raw trancript, if it was succesfully sent, then flag is set to True
        
        quality, snr_db, flatness,hf_ratio = classify_audio_quality(best_audio, sr=sr)

        if quality == "clean":
            print("Audio classified as clean -> skipping filtering.")
            #I havent added it here, but im thinking of adding one of the checks i have written to see if the transcript has repetetive words/sentences, and if it does to clean it up then resend it to the frontend again. But right now, if we are here then the audio is clean and we just keep the raw trancript as the final one


        # ===== Stage 2: Band-pass (conditional) =====
        elif quality == "moderate":
            print("Audio is moderately noisy, applying bandpass.")
            bp_audio = bandpass_filter(best_audio)
            bp_result = whisper_decode(whisper_model, bp_audio)
            best_result = compare_and_update(best_result, bp_result, "band-pass")
            best_audio = bp_audio
            #If we are here then we have applied bandpass filter only, then compared the old best_result transcript with the new best_result transcript and keep only the one who is the best. This i need to fix, because what happens right now is that whichever transcript is the best, overrides the previous one. I will write the code that saves this transcript as well later today.
            # Here will be the code that saves the intermediate transcript to backend as well, if it was succesfully sent, then flag is set to True
        
         # ===== Stage 3: Band-pass + Pre-emphasis (conditional) =====
        elif quality == "muffled":
            print("Audio is muffled, applying bandpass and pre-emphasis.")
            bp_audio = bandpass_filter(best_audio)
            pe_audio = pre_emphasis(bp_audio)
            pe_result = whisper_decode(whisper_model, pe_audio)
            best_result = compare_and_update(best_result, pe_result, "band-pass+PE")
            best_audio = pe_audio
            #If we are here, then we have applied bandpass + pre-emphasis, and we (will) have another intermediate trancript that needs to be send to the backend as well, if it was succesfully sent, then flag is set to True

        # ===== Stage 4: SEMamba + Bandpass +PE if needed (conditional) =====
        elif quality == "noisy":  #run SEMamba only when noisy enough
            print("Audio is noisy, applying SEmamba and bandpass.")
        
        # If clip is long (> 4 minutes) use chunked processing to avoid OOM
            clip_seconds = len(best_audio) / float(sr)
            if clip_seconds > 4 * 60:
                print(f"Long clip ({clip_seconds/60:.2f} min) detected: using chunked SEMamba denoise.")
                mamba_audio = semamba_denoise_chunks(best_audio, sr, model, device, n_fft, hop_size, win_size, compress_factor=0.8, chunk_size_sec=8.0, overlap_sec=2.0)
          
            else:
                noisy_wav = torch.FloatTensor(best_audio).to(device)
                norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
                
                noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
                noisy_amp, noisy_pha, _ = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor=0.8)
                
                noisy_amp = noisy_amp.to(device).half()
                noisy_pha = noisy_pha.to(device).half()

                amp_g, pha_g, _ = model(noisy_amp, noisy_pha)
                mamba_audio = mag_phase_istft(amp_g.float(), pha_g.float(), n_fft, hop_size, win_size, compress_factor=0.8)
                #mamba_audio = (mamba_audio / norm_factor).squeeze().cpu().detach().numpy()

                mamba_audio = (mamba_audio / norm_factor.cpu().item())
                mamba_audio = mamba_audio.squeeze().cpu().detach().numpy()

                mamba_audio = mamba_audio / (np.max(np.abs(mamba_audio)) + 1e-9)

                del amp_g, pha_g, noisy_amp, noisy_pha
                torch.cuda.empty_cache()
                
            # --- Always bandpass after SEMamba ---
            mamba_audio = bandpass_filter(mamba_audio, 80, 7000)

            # --- Conditional pre-emphasis ---
            fft = np.abs(np.fft.rfft(mamba_audio))**2
            freqs = np.fft.rfftfreq(len(mamba_audio), 1/sr)
            hf_energy = fft[(freqs > 3000) & (freqs < 8000)].sum()
            lf_energy = fft[freqs <= 3000].sum()
            hf_ratio = hf_energy / (lf_energy + 1e-9)

            stage_name = "SEMamba+BP"
            if hf_ratio < 0.02:
                print("Post-Mamba audio still muffled -> applying pre-emphasis.")
                mamba_audio = pre_emphasis(mamba_audio)
                stage_name += "+PE"
                # here we have applied mamba+bandpass+pre emphasis, and we (will) have another intermediate transcript to send to backend as well, if it was succesfully sent, then flag is set to True. Right now we dont have a transcript generated here, but we will have it after i write the code

            if args.post_processing_PCS:
                mamba_audio = cal_pcs(mamba_audio)
        
            mamba_result = whisper_decode(whisper_model, mamba_audio)
            best_result = compare_and_update(best_result, mamba_result, stage_name)
            best_audio = mamba_audio
            #here we will have another intermediate transcript. I have to reorganize this part of the code a bit so that its before the pre emphasis and pcs, so that i can save the transcript before those two filters are applied as well. If it was succesfully sent, then flag is set to True

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

                #here we will have the final intermediate transcript, that will be sent to the backend as well, if it was succesfully sent, then flag is set to True
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

        #Here we will send the final transript to the backend, if it was succesfully sent, then flag is set to True

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

