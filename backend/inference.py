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
from utils.util import load_config
import datetime
from collections import Counter
from snr_helpers import estimate_snr_vad, classify_audio_quality
from helpers_and_filters import bandpass_filter, pre_emphasis, run_deepfilternet, str2bool, semamba_denoise_chunks, save_intermediate_transcript
from transcription_comparison import cleanup_repetition, compare_and_update
from db import insert_intermediate_record,set_success_status,add_audio_path
import dotenv

# Load environment variables for database connection
dotenv.load_dotenv()


h = None
device = None 

# ------------------------------
# Whisper config
# ------------------------------

DOMAIN_PROMPT = (
    "Der Input sind Funksprüche von Rettungseinsätzen in Hamburg. Alle hörbaren Wörter (einschließlich Orts- und Straßennamen) exakt wiedergeben. Keine zusätzlichen Wörter erfinden oder ergänzen. Zahlen als Ziffern darstellen. Unverständliche Stellen mit '...' markieren. Kurze Sätze, einfache Grammatik."
)

def whisper_decode(model, audio_array, language=None):
    
     #ensure no negative strides by copying
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
        word_timestamps=True
    )


# ------------------------------
# Core pipeline
# ------------------------------

def inference(args, device):

    # current id for database access
    current_id = int(args.current_id)

    cfg = load_config(args.config)
    n_fft, hop_size, win_size = cfg['stft_cfg']['n_fft'], cfg['stft_cfg']['hop_size'], cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    
    model = SEMamba(cfg).to(device).half()

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
        best_result["text"] = cleanup_repetition(best_result["text"])
        #save_intermediate_transcript(base, stage, best_result)
        print(f"Stage RAW text: {best_result.get('text','').strip()}")

        # Here is where we insert the raw transcript into the database
        insert_intermediate_record(best_result["text"].strip(), 1,current_id)
        if(best_result["text"]):
            set_success_status(current_id, True)  
        
        quality, snr_db, flatness,hf_ratio = classify_audio_quality(best_audio, sr=sr)

        if quality == "clean":
            print("Audio classified as clean -> skipping filtering.")
            stage = "final"
            #save_intermediate_transcript(base, stage, best_result)

        # ===== Stage 2: Band-pass (conditional) =====
        elif quality == "moderate":
            print("Audio is moderately noisy, applying bandpass.")
            bp_audio = bandpass_filter(best_audio)
            bp_result = whisper_decode(whisper_model, bp_audio)
            stage = "bandpass"
            #save_intermediate_transcript(base, stage, bp_result)
            best_result = compare_and_update(best_result, bp_result, stage)
            best_audio = bp_audio

            insert_intermediate_record(bp_result["text"].strip(), 6,current_id)
                   
         # ===== Stage 3: Band-pass + Pre-emphasis (conditional) =====
        elif quality == "muffled":
            print("Audio is muffled, applying bandpass and pre-emphasis.")
            bp_audio = bandpass_filter(best_audio)
            pe_audio = pre_emphasis(bp_audio)
            pe_result = whisper_decode(whisper_model, pe_audio)
            stage = "bandpass+PE"
            #save_intermediate_transcript(base, stage, pe_result)
            best_result = compare_and_update(best_result, pe_result, stage)
            best_audio = pe_audio

            insert_intermediate_record(pe_result["text"].strip(), 2,current_id)
           
        # ===== Stage 4: SEMamba + Bandpass +PE if needed (conditional) =====
        elif quality == "noisy":  #run SEMamba only when noisy enough
            print("Audio is noisy, applying SEmamba and bandpass.")
            stage = "SEMamba+BP"
        
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

            if args.post_processing_PCS:
                mamba_audio = cal_pcs(mamba_audio)
        
            
            mamba_result = whisper_decode(whisper_model, mamba_audio)
            #save_intermediate_transcript(base, stage, mamba_result)
            best_result = compare_and_update(best_result, mamba_result, stage)
            best_audio = mamba_audio
            insert_intermediate_record(mamba_result["text"].strip(), 3,current_id)
            
            if hf_ratio < 0.02:
                print("Post-Mamba audio still muffled -> applying pre-emphasis.")
                mamba_audio = pre_emphasis(mamba_audio)
                stage += "+PE"
                mamba_pe_result = whisper_decode(whisper_model, mamba_audio) 
                #save_intermediate_transcript(base, stage, mamba_pe_result)
                best_result = compare_and_update(best_result, mamba_pe_result, stage)
                best_audio = mamba_audio

                insert_intermediate_record(mamba_pe_result["text"].strip(), 4,current_id)
               
            # ===== Stage 5: DeepFilterNet (conditional) =====
            snr_post = estimate_snr_vad(best_audio, sr=16000)
            flatness_post = librosa.feature.spectral_flatness(S=np.abs(librosa.stft(best_audio))).mean()
            if snr_post < 15 and flatness_post < 0.01:
                print(f"SNR Post={snr_post:.2f} dB, flatness post={flatness_post:.4f}")
                print("Audio is still noisy, applying DeepFilterNet.")
                stage = "DeepFilterNet"

                tmp_dir = "tmp"
                os.makedirs(tmp_dir, exist_ok=True)
                dfn_path = os.path.join(tmp_dir, f"{base}_dfn.wav")
                sf.write(dfn_path, best_audio, 16000, 'PCM_16')
                
                run_deepfilternet(dfn_path, tmp_dir)
                
                dfn_audio, _ = librosa.load(dfn_path, sr=16000, mono=True)
                dfn_result = whisper_decode(whisper_model, dfn_audio)
                #save_intermediate_transcript(base, stage, dfn_result)
                best_result = compare_and_update(best_result, dfn_result, stage)
                best_audio = dfn_audio

                insert_intermediate_record(dfn_result["text"].strip(), 5,current_id)
                
                os.remove(dfn_path)

        # Save final
        sf.write(final_wav_out, best_audio, 16000, 'PCM_16')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        best_result["timestamp"] = timestamp
        best_result["text"] = cleanup_repetition(best_result["text"])
        #save_intermediate_transcript(base, "final", best_result)

        add_audio_path(current_id, final_wav_out,1) # 1 for output audio path

        # Here is where we insert the final transcript into the database
        insert_intermediate_record(best_result["text"].strip(), 0,current_id)
        
        print(f"\nFINAL TEXT   : {best_result.get('text','').strip()}")
        print(f"SAVED WAV    : {final_wav_out}")
        print(f"SAVED JSON   : {base}")


def main():
    print('Initializing Inference Process..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', default='test_sounds')
    parser.add_argument('--output_folder', default='results')
    parser.add_argument('--config', default='results')
    parser.add_argument('--checkpoint_file', required=True)
    parser.add_argument('--post_processing_PCS', type=str2bool, default=False)
    parser.add_argument('--file', type=str, default=None, help='Specific file to process')
    parser.add_argument('--current_id', type=int, default=None, help='Current ID for database record')
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

