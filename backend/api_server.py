import os, re, uuid, subprocess
from typing import List, Set, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import delete_records, select_records, get_latest_id, create_new_record, add_audio_path, select_transcriptions, select_intermediate_result
from geocoding import geocode_one, extract_candidates
import dotenv
import asyncio
from fastapi import Request
import datetime

dotenv.load_dotenv()

app = FastAPI()
logs_store = {}
pending_responses = {}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------ Paths & helpers ------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_DIR = os.getenv("INPUT_AUDIO_DIR", os.path.join(BASE_DIR, "input_audio"))
OUTPUT_AUDIO_DIR = os.getenv("OUTPUT_AUDIO_DIR", os.path.join(BASE_DIR, "output_audio"))
OUTPUT_TRANSCRIPT_DIR = os.getenv("OUTPUT_TRANSCRIPT_DIR", os.path.join(BASE_DIR, "output_transcriptions"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
        )
    return p

def convert_webm_to_wav(webm_path, wav_path):
    run(["ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", wav_path])

def delete_old_records(records):
    for record in records:
        print("deleting files from record with id: ", record[0])

        try:
            if record[1]:
                print("deleting input audio file: ", record[1])
                os.remove(record[1])
        except Exception as e:
            print("could not delete input audio file: ", e)

        try:
            if record[2]:
                print("deleting output audio file: ", record[2])
                os.remove(record[2])
        except Exception as e:
            print("could not delete output audio file: ", e)


# ------ REQUESTS    ------


@app.post("/transcribe-audio/")
@app.post("/transcribe-audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        unique_id = uuid.uuid4().hex[:8]
        base, ext = os.path.splitext(file.filename or "audio.webm")
        ext = ext or ".webm"
        webm_name = f"{base}_{unique_id}{ext}"
        webm_path = os.path.join(UPLOAD_DIR, webm_name)

        with open(webm_path, "wb") as f:
            f.write(await file.read())

        wav_filename = f"{base}_{unique_id}.wav"
        wav_location = os.path.join(UPLOAD_DIR, wav_filename)
        convert_webm_to_wav(webm_path, wav_location)
        os.remove(webm_path)

        create_new_record()
        current_id = str(get_latest_id())
        add_audio_path(current_id, wav_location, 0)

        env = os.environ.copy()
        env.update({
            "INPUT_AUDIO_DIR": UPLOAD_DIR,
            "OUTPUT_AUDIO_DIR": OUTPUT_AUDIO_DIR
        })

        subprocess.Popen(
            [
                "python", "inference.py",
                "--output_folder", OUTPUT_AUDIO_DIR,
                "--input_folder", UPLOAD_DIR,
                "--checkpoint_file", "ckpts/SEMamba_advanced.pth",
                "--config", "recipes/SEMamba_advanced/SEMamba_advanced.yaml",
                "--post_processing_PCS", "False",
                "--file", wav_filename,
                "--current_id", current_id
            ],
            cwd=os.path.abspath(os.path.dirname(__file__))
        )

        old_records = delete_records()
        delete_old_records(old_records)
        

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        pending_responses[current_id] = fut
        return await fut

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcription-ready")
async def transcription_ready(request: Request):
    """Called by inference.py when raw transcript is ready"""
    data = await request.json()
    current_id = str(data["id"])
    record = select_intermediate_result(current_id, 1)

    fut = pending_responses.pop(current_id, None)
    if fut:
        fut.set_result(JSONResponse(content={
            "transcription": record,
            "id": int(current_id)
        }))
    return {"status": "ok"}


@app.get("/get-intermediate-transcript/{id}")
async def get_intermediate_transcript(id: int):
    try:
        transcripts = select_transcriptions(id)

        return JSONResponse(content={"transcripts": transcripts})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-update")
async def log_update(request: Request):
    data = await request.json()
    current_id = str(data["id"])
    message = data["message"]

    if current_id not in logs_store:
        logs_store[current_id] = []
    logs_store[current_id].append({
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })

    return JSONResponse(content={"ok": True})


@app.get("/get-logs/{id}")
async def get_logs(id: int):
    current_id = str(id)
    logs = logs_store.get(current_id, [])
    return JSONResponse(content={"logs": logs})


@app.get("/get-history/")
async def get_history():
    old_records = delete_records()
    delete_old_records(old_records)
    records = select_records()
    return JSONResponse(content={"history": records})

class GeocodeIn(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None

@app.post("/geocode")
async def geocode(payload: GeocodeIn, debug: bool = Query(False)):
    texts = payload.texts if payload.texts else ([payload.text] if payload.text else [])
    if not texts:
        raise HTTPException(status_code=400, detail="Provide `text` or `texts`.")

    candidates: Set[str] = set()
    for t in texts:
        candidates.update(extract_candidates(t))

    markers, dbg = [], []
    for cand in candidates:
        try:
            hit = await geocode_one(cand)
            dbg.append({"candidate": cand, "hit": bool(hit)})
            if hit:
                markers.append(hit)
        except Exception as e:
            dbg.append({"candidate": cand, "error": str(e)})

    resp = {"markers": markers, "meta": {"candidates": list(candidates), "count": len(markers)}}
    if debug:
        resp["debug"] = dbg
    return resp