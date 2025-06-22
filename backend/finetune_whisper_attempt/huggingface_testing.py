from datasets import load_dataset, Audio

dataset = load_dataset(
    "csv",
    data_files="training_dataset/all_transcriptions.csv",
    split="train"
)
dataset = dataset.cast_column("audio_file", Audio(sampling_rate=16000))
print(dataset[0])