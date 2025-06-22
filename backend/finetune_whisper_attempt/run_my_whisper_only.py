#!/usr/bin/env python
import argparse
import torch
import soundfile as sf
import librosa
from transformers import WhisperProcessor, WhisperForConditionalGeneration

def transcribe_file(
    processor,
    model,
    audio_path: str,
    language: str,
    device: torch.device,
    chunk_length_s: float,
):
    # 1) load & resample entire audio
    audio, sr = sf.read(audio_path, dtype="float32")
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        sr = 16000

    # 2) split into non-overlapping chunks of chunk_length_s
    chunk_size = int(chunk_length_s * sr)
    chunks = [
        audio[i : i + chunk_size]
        for i in range(0, len(audio), chunk_size)
        if i < len(audio)
    ]

    texts = []
    for idx, chunk in enumerate(chunks):
        # skip too-short final chunk if you like
        if chunk.shape[0] < 0.1 * sr:
            break

        # 3) build model inputs
        inputs = processor(chunk, sampling_rate=sr, return_tensors="pt")
        input_features = inputs.input_features.to(device)

        # 4) generate & decode
        # with torch.no_grad():
        #     generated_ids = model.generate(
        #         input_features,
        #         max_length=model.config.max_target_positions,
        #         num_beams=1,        # greedy to save memory
        #         do_sample=False,
        #     )


        with torch.no_grad():
            generated_ids = model.generate(
                input_features,
                max_length=model.config.max_target_positions,
                num_beams=1,        # greedy
                do_sample=False,
                use_cache=False,    # << disable KV-cache
            )


        text = processor.tokenizer.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]
        texts.append(text)

    # 5) join chunk-level transcripts with spaces
    return " ".join(texts).strip()

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe one audio file with your fine-tuned Whisper model, in small chunks"
    )
    parser.add_argument("--whisper_dir",  required=True,
                        help="path to your fine-tuned Whisper folder")
    parser.add_argument("--audio_path",   required=True,
                        help="path to a single audio file to transcribe")
    parser.add_argument("--language",      default="de",
                        help="language code (e.g. 'en', 'de') you fine-tuned for")
    parser.add_argument("--device",       default=None,
                        help="torch device (cuda or cpu). Default: cuda if available")
    parser.add_argument("--chunk_length", type=float, default=1.0,
                        help="length (in seconds) of each audio chunk (default: 5s)")
    args = parser.parse_args()

    # pick device
    device = torch.device(
        args.device if args.device
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    # load once
    processor = WhisperProcessor.from_pretrained(args.whisper_dir)
    model     = WhisperForConditionalGeneration.from_pretrained(
        args.whisper_dir,
        torch_dtype=torch.float32
    )


    # quantize on CPU if needed
    if device.type == "cpu":
        model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
    model.to(device).eval()
    # force your language/task prompt
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language=args.language, task="transcribe"
    )

    # transcribe in chunks
    transcription = transcribe_file(
        processor, model,
        audio_path=args.audio_path,
        language=args.language,
        device=device,
        chunk_length_s=args.chunk_length,
    )
    print(transcription)

if __name__ == "__main__":
    main()