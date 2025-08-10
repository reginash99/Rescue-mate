from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import os
import subprocess
import glob
import datetime
import uuid

UPLOAD_DIR = "./input_audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def convert_webm_to_wav(webm_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", wav_path
    ], check=True)

@app.post("/transcribe-audio/")
async def upload_audio(file: UploadFile = File(...)):
     # Generate a unique filename
    #timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    base, ext = os.path.splitext(file.filename)
    unique_filename = f"{base}_{unique_id}{ext}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_location, "wb") as f:
        f.write(await file.read())

    # Convert to WAV if needed
    base, _ = os.path.splitext(unique_filename)
    wav_filename = f"{base}.wav"
    wav_location = os.path.join(UPLOAD_DIR, wav_filename)
    convert_webm_to_wav(file_location, wav_location)

    os.remove(file_location)

    backend_dir = os.path.abspath(os.path.dirname(__file__))

    # Run the inference pipeline, passing the unique file as input
    # (You may need to modify pretrained.sh and inference.py to accept a specific file)
    subprocess.run(["sh", "pretrained.sh", wav_filename], cwd=backend_dir, check=True)

    # Find the latest JSON transcription
    transcription_files = glob.glob("./output_transcriptions/*.json")
    latest_transcription = max(transcription_files, key=os.path.getmtime)
    with open(latest_transcription, "r", encoding="utf-8") as f:
        transcription_data = f.read()

    return JSONResponse(content={"transcription": transcription_data})



# @app.get("/get-audio/{filename}")
# async def get_audio(filename: str):
#     file_path = os.path.join(UPLOAD_DIR, filename)
#     if not os.path.exists(file_path):
#         return {"error": "File not found"}
#     return FileResponse(file_path)