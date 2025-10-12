import os, uuid, subprocess, asyncio, datetime
from typing import List, Set, Optional, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    delete_records, select_records, get_latest_id, create_new_record,
    add_audio_path, select_transcriptions, select_intermediate_result
)
from geocoding import geocode_one, extract_candidates
import dotenv

dotenv.load_dotenv()

# single app instance
app = FastAPI(redirect_slashes=True)

# allow all (docker-friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------ state ------
logs_store: Dict[str, list[dict]] = {}
pending_responses: Dict[str, asyncio.Future] = {}

# ------ paths ------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.getenv("INPUT_AUDIO_DIR", os.path.join(BASE_DIR, "input_audio"))
OUTPUT_AUDIO_DIR = os.getenv("OUTPUT_AUDIO_DIR", os.path.join(BASE_DIR, "output_audio"))
OUTPUT_TRANSCRIPT_DIR = os.getenv("OUTPUT_TRANSCRIPT_DIR", os.path.join(BASE_DIR, "output_transcriptions"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)

# ------ helpers ------
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
        try:
            if record[1]:
                os.remove(record[1])
        except Exception:
            pass
        try:
            if record[2]:
                os.remove(record[2])
        except Exception:
            pass

# ------ routes ------

@app.post("/transcribe-audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        unique_id = uuid.uuid4().hex[:8]
        base, ext = os.path.splitext(file.filename or "audio.webm")
        ext = ext or ".webm"

        webm_name = f"{base}_{unique_id}{ext}"
        webm_path = os.path.join(UPLOAD_DIR, webm_name)

        content = await file.read()
        with open(webm_path, "wb") as f:
            f.write(content)

        wav_filename = f"{base}_{unique_id}.wav"
        wav_location = os.path.join(UPLOAD_DIR, wav_filename)
        convert_webm_to_wav(webm_path, wav_location)
        os.remove(webm_path)

        create_new_record()
        current_id = str(get_latest_id())
        add_audio_path(current_id, wav_location, 0)

        # pass env to subprocess (docker-friendly)
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
            cwd=os.path.abspath(os.path.dirname(__file__)),
            env=env
        )

        old_records = delete_records()
        delete_old_records(old_records)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        pending_responses[current_id] = fut
        return await fut

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcription-ready")
async def transcription_ready(request: Request):
    """Called by inference.py when raw transcript is ready"""
    try:
        data = await request.json()
        current_id = str(data.get("id"))
        if not current_id:
            raise HTTPException(status_code=400, detail="Missing id")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        record = select_intermediate_result(current_id, 1)
    except Exception:
        record = None

    fut = pending_responses.pop(current_id, None)
    if fut and not fut.done():
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
    try:
        data = await request.json()
        current_id = str(data.get("id"))
        message = data.get("message", "")
        if not current_id:
            raise HTTPException(status_code=400, detail="Missing id")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logs_store.setdefault(current_id, []).append({
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })
    return JSONResponse(content={"ok": True})


@app.get("/get-logs/{id}")
async def get_logs(id: int):
    current_id = str(id)
    logs = logs_store.get(current_id, [])
    return JSONResponse(content={"logs": logs})


@app.get("/get-history")
async def get_history():
    old_records = delete_records()
    delete_old_records(old_records)
    records = select_records()
    return JSONResponse(content={"history": records})


class GeocodeIn(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None

from fastapi.encoders import jsonable_encoder

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
            if debug:
                dbg.append({"candidate": cand, "hit": bool(hit)})
            if hit:
                markers.append(hit)
        except Exception as e:
            if debug:
                dbg.append({"candidate": cand, "error": str(e)})

    resp = {
        "markers": markers,                         # list[dict]
        "meta": {"candidates": list(candidates), "count": len(markers)},
        **({"debug": dbg} if debug else {}),
    }
    return JSONResponse(content=jsonable_encoder(resp))

