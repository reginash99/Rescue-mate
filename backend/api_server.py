from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import os
import subprocess
import glob
import datetime
import uuid
import json
from db import insert_record, delete_records, select_records, get_id, get_latest_id, select_record,create_new_record, add_audio_path
import dotenv

dotenv.load_dotenv()

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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
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

    # Initialize database with a new record to get an ID for intermediate updates
    create_new_record()
    current_id = str(get_latest_id())
    add_audio_path(current_id, wav_location,0) # 0 for input audio path

    # Run the inference pipeline, passing the unique file as input
    # (You may need to modify pretrained.sh and inference.py to accept a specific file)
    subprocess.run(["sh", "pretrained.sh", wav_filename,current_id], cwd=backend_dir, check=True)

    # Find the latest JSON transcription
    '''transcription_files = glob.glob("./output_transcriptions/*.json")
    latest_transcription = max(transcription_files, key=os.path.getmtime)
    with open(latest_transcription, "r", encoding="utf-8") as f:
        transcription_data = f.read()
        transcription_data_json = json.loads(transcription_data)

    #flag_status =  '1' if transcription_data_json['status'] !== '' else '0'
    flag_status = True # placeholder until status is added to json structure    
    # Insert record into the database
    insert_record(transcription_data_json['timestamp'], transcription_data_json['text'], flag_status)
    #insert_record(datetime.datetime.now(), transcription_data_json['text'])
    current_id = get_id(transcription_data_json['timestamp'], transcription_data_json['text'],flag_status)'''

    # delete all records older that 24 hours
    #delete_records()
    
    json_data = select_record(current_id)
    print(json_data)

    return JSONResponse(content={"transcription": json_data})

@app.get("/get-history/")
async def get_history(): 
    #delete_records()
    records = select_records()
    return JSONResponse(content={"history": records})

# temporary endpoint to simulate transcription insertion -- mocking the current transcription process
#@app.post("/transcribe-audio/")
async def placeholder_recording():
    '''transcription_files = glob.glob(r".\Polizei_10_20250913_140821.json")
    latest_transcription = max(transcription_files, key=os.path.getmtime)
    with open(latest_transcription, "r", encoding="utf-8") as f:
        transcription_data = f.read()
        transcription_data_json = json.loads(transcription_data)
    #print("json ", transcription_data)
    flag_status =  transcription_data_json['successful_transcription']

    #flag_status = 0 # placeholder until status is added to json structure    
    # Insert record into the database
    datetime_ = datetime.datetime.now()
    insert_record(datetime_, transcription_data_json['text'],flag_status)
    current_id = get_id(datetime_, transcription_data_json['text'],flag_status)
    transcription_data_json['timestamp'] = datetime_.strftime("%d.%m.%Y  %H:%M:%S")
    transcription_data_json['status'] = flag_status
    transcription_data_json['id'] = current_id
    print(transcription_data_json)'''
    
    latest_id = get_latest_id()
    json_data = select_record(latest_id)
    print(json_data)

    return JSONResponse(content={"transcription": json_data})


# @app.get("/get-audio/{filename}")
# async def get_audio(filename: str):
#     file_path = os.path.join(UPLOAD_DIR, filename)
#     if not os.path.exists(file_path):
#         return {"error": "File not found"}
#     return FileResponse(file_path)