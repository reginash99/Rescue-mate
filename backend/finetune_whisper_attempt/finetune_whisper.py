from datasets import load_dataset, Audio
from transformers import WhisperForConditionalGeneration, WhisperProcessor, Seq2SeqTrainingArguments, Seq2SeqTrainer, EarlyStoppingCallback
import evaluate
#from transformers.data.data_collator import DataCollatorSpeechSeq2Seq
from typing import List, Dict


# Load and split dataset
dataset = load_dataset(
    "csv",
    data_files="training_dataset/all_transcriptions.csv",
    split="train"
)
dataset = dataset.cast_column("audio_file", Audio(sampling_rate=16000))
dataset = dataset.train_test_split(test_size=0.2, seed=42)
train_dataset = dataset["train"]
eval_dataset = dataset["test"]

# Load model and processor
model_name = "openai/whisper-small"
model = WhisperForConditionalGeneration.from_pretrained(model_name)
processor = WhisperProcessor.from_pretrained(model_name)
max_target_length = model.config.max_target_positions  # usually 448


def speech_data_collator(batch: List[Dict]):
    # 1) collect
    input_features = [ex["input_features"] for ex in batch]
    labels         = [ex["labels"] for ex in batch]

    # 2) pad audio_features to longest in batch (returns a dict with "input_features")
    audio_batch = processor.feature_extractor.pad(
        {"input_features": input_features},
        return_tensors="pt"
    )

    # 3) pad label sequences (token ids) to longest in batch
    label_batch = processor.tokenizer.pad(
        {"input_ids": labels},
        return_tensors="pt",
        padding=True
    )
    # convert pad_token_id to -100 so that loss ignores these positions
    label_batch["input_ids"][label_batch["input_ids"] == processor.tokenizer.pad_token_id] = -100

    return {
        "input_features": audio_batch["input_features"],
        "labels":         label_batch["input_ids"],
    }


# Preprocessing function
def preprocess(batch):
    audio = batch["audio_file"]["array"]
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    batch["input_features"] = inputs.input_features[0]
    labels = processor.tokenizer(
        batch["transcription"],
        max_length=max_target_length,
        truncation=True,
    ).input_ids

    batch["labels"] = labels    

    return batch


# Filter out samples with too-long transcriptions
def is_short_enough(batch):
    # tokenize with truncation turned off just to count
    length = len(processor.tokenizer(batch["transcription"]).input_ids)
    return length <= max_target_length


train_dataset = train_dataset.filter(is_short_enough)
eval_dataset = eval_dataset.filter(is_short_enough)

train_dataset = train_dataset.map(preprocess, remove_columns=train_dataset.column_names, num_proc=4)
eval_dataset = eval_dataset.map(preprocess, remove_columns=eval_dataset.column_names, num_proc=4)

# WER metric
wer_metric = evaluate.load("wer")
def compute_metrics(pred):
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    pred_str = processor.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
    return {"wer": wer_metric.compute(predictions=pred_str, references=label_str)}


# Training arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./whisper-finetuned-radio",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=2,
    learning_rate=1e-5,
    num_train_epochs=3,
    fp16=True,
    save_strategy="epoch",           # <-- set to "epoch"
    logging_steps=10,
    evaluation_strategy="epoch",     # <-- already "epoch"
    report_to="none",
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    predict_with_generate=True,
    generation_max_length=max_target_length,  # <--- optional cap
    generation_num_beams=4,
)

# Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=speech_data_collator,
    #tokenizer=processor.feature_extractor,
    tokenizer=processor.tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
)

trainer.train()

trainer.save_model("my-whisper-small-finetuned") 
processor.save_pretrained("my-whisper-small-finetuned")