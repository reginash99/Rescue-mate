import pandas as pd
import os

csv_path = "training_dataset/all_transcriptions.csv"
df = pd.read_csv(csv_path)
df["audio_file"] = "training_dataset/" + df["audio_file"].astype(str)
df.to_csv(csv_path, index=False)


# csv_path = "training_dataset/all_transcriptions.csv"
# audio_base = "backend"  # base path for relative audio_file entries

# df = pd.read_csv(csv_path)
# def file_exists(row):
#     return os.path.exists(os.path.join(audio_base, row["audio_file"]))

# df_clean = df[df.apply(file_exists, axis=1)]
# print(f"Kept {len(df_clean)} of {len(df)} rows (removed {len(df)-len(df_clean)} missing files)")
# df_clean.to_csv(csv_path, index=False)