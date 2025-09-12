import librosa
import numpy as np
import webrtcvad

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

    #background RMS check
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
