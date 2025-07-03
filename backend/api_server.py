from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import os
import subprocess
import glob

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

@app.post("/transcribe-audio/")
async def upload_audio(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())


    backend_dir = os.path.abspath(os.path.dirname(__file__))

    # Run the inference pipeline
    subprocess.run(["sh", "pretrained.sh"], cwd=backend_dir, check=True)

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