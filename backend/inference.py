# api_server.py
import os, re, uuid, subprocess, time, unicodedata, datetime, asyncio, logging
from typing import List, Set, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import dotenv
import psycopg  # used indirectly via db.py, keep import if you rely on it elsewhere

# DB helpers
from db import (
    delete_records, select_records, get_latest_id, create_new_record,
    add_audio_path, select_transcriptions, select_intermediate_result
)

dotenv.load_dotenv()

# ---------- App & logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

# Create the app ONCE (redirect_slashes to normalize /foo and /foo/)
app = FastAPI(redoc_url=None, docs_url=None, redirect_slashes=True)

# CORS (kept wide because you proxy in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores
logs_store: dict[str, list[dict]] = {}
pending_responses: dict[str, asyncio.Future] = {}

# ---------- Health ----------
@app.get("/healthy")
@app.get("/healthy/")
def healthy():
    return {"status": "ok"}

# ---------- Paths & helpers ----------
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

# ---------- Upload & kickoff ----------
@app.post("/transcribe-audio")
@app.post("/transcribe-audio/")
async def upload_audio(file: UploadFile = File(...)):
    t0 = time.time()
    try:
        log.info("UPLOAD: received filename=%s content_type=%s", file.filename, file.content_type)

        unique = uuid.uuid4().hex[:8]
        base, ext = os.path.splitext(file.filename or "audio.webm")
        ext = ext or ".webm"
        webm_name = f"{base}_{unique}{ext}"
        webm_path = os.path.join(UPLOAD_DIR, webm_name)

        raw = await file.read()
        log.info("UPLOAD: bytes=%d -> %s", len(raw), webm_path)
        with open(webm_path, "wb") as f:
            f.write(raw)

        # Convert -> WAV
        wav_name = f"{base}_{unique}.wav"
        wav_path = os.path.join(UPLOAD_DIR, wav_name)
        log.info("FFMPEG: converting %s -> %s", webm_path, wav_path)
        convert_webm_to_wav(webm_path, wav_path)
        os.remove(webm_path)
        log.info("FFMPEG: done; wav exists=%s size=%d", os.path.exists(wav_path), os.path.getsize(wav_path))

        # DB row
        create_new_record()
        current_id = str(get_latest_id())
        add_audio_path(current_id, wav_path, 0)
        log.info("DB: created record id=%s with input=%s", current_id, wav_path)

        # Start inference (non-blocking)
        cmd = [
            "python", "inference.py",
            "--output_folder", OUTPUT_AUDIO_DIR,
            "--input_folder", UPLOAD_DIR,
            "--checkpoint_file", "ckpts/SEMamba_advanced.pth",
            "--config", "recipes/SEMamba_advanced/SEMamba_advanced.yaml",
            "--post_processing_PCS", "False",
            "--file", wav_name,
            "--current_id", current_id
        ]
        log.info("SPAWN: %s", " ".join(cmd))
        p = subprocess.Popen(cmd, cwd=os.path.abspath(os.path.dirname(__file__)))
        log.info("SPAWN: pid=%s", p.pid)

        # Clean up old DB rows + files
        old_records = delete_records()
        delete_old_records(old_records)

        # Wait for inference to signal ready—but not forever
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        pending_responses[current_id] = fut

        timeout_sec = 180  # adjust if needed
        log.info("RETURN: waiting for inference… (elapsed %.2fs, timeout %ss)", time.time() - t0, timeout_sec)
        try:
            return await asyncio.wait_for(fut, timeout=timeout_sec)
        except asyncio.TimeoutError:
            pending_responses.pop(current_id, None)
            raise HTTPException(status_code=504, detail="Inference timed out")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("UPLOAD: failed")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Callback from inference ----------
@app.post("/transcription-ready")
@app.post("/transcription-ready/")
async def transcription_ready(request: Request):
    """Called by inference.py when RAW transcript is stored in DB."""
    data = await request.json()
    current_id = str(data.get("id"))
    if not current_id:
        raise HTTPException(status_code=400, detail="Missing id")

    # stage 1 = RAW in your code
    record = select_intermediate_result(current_id, 1)

    fut = pending_responses.pop(current_id, None)
    if fut and not fut.done():
        fut.set_result(JSONResponse(content={
            "transcription": record,
            "id": int(current_id)
        }))
    return {"status": "ok"}

# ---------- Intermediate transcripts / logs ----------
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
    current_id = str(data.get("id"))
    message = data.get("message", "")
    if not current_id:
        raise HTTPException(status_code=400, detail="Missing id")

    logs_store.setdefault(current_id, []).append({
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    })
    return JSONResponse(content={"ok": True})

@app.get("/get-logs/{id}")
async def get_logs(id: int):
    current_id = str(id)
    logs = logs_store.get(current_id, [])
    return JSONResponse(content={"logs": logs})

# ---------- History ----------
@app.get("/get-history")
@app.get("/get-history/")
async def get_history():
    old_records = delete_records()
    delete_old_records(old_records)
    records = select_records()
    return JSONResponse(content={"history": records})

# ---------- Geocoding ----------
import httpx  # used below
HAMBURG_VIEWBOX = dict(left=8.4, top=53.95, right=10.5, bottom=53.3)

poi_list = [
    "Elbphilharmonie","Miniatur Wunderland","HafenCity","Landungsbrücken",
    "Schanzenviertel","St. Pauli","Reeperbahn","Planten un Blomen","Altona",
    "Hauptbahnhof","Dammtor","Jungfernstieg","Binnenalster","Außenalster",
    "Rathausmarkt","Speicherstadt","Fischmarkt","Eppendorf","Winterhude",
]

SUFFIX_WORD = r"(?:Stra(?:ße|sse)|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer|Stieg)"

ATTACHED = re.compile(
    rf"\b([A-ZÄÖÜ][\wÄÖÜäöüß\-]*(?:{SUFFIX_WORD}))(?:\s+(\d+[a-zA-Z]?))?\b",
    re.IGNORECASE | re.UNICODE,
)
SEPARATED = re.compile(
    rf"\b([A-ZÄÖÜ][\wÄÖÜäöüß\-]+(?:[ -][A-ZÄÖÜ][\wÄÖÜäöüß\-]+)*)\s{SUFFIX_WORD}(?:\s+(\d+[a-zA-Z]?))?\b",
    re.IGNORECASE | re.UNICODE,
)

def normalize_query(q: str) -> str:
    if not q: return q
    s = q.strip()
    s = re.sub(r'\bStr\.\b', 'Straße', s, flags=re.IGNORECASE)
    s = re.sub(r'\bStrasse\b', 'Straße', s, flags=re.IGNORECASE)
    return s

def variants(q: str) -> list[str]:
    if not q: return []
    s = normalize_query(q)
    out = {s, s.replace('ß', 'ss'), s.replace('ss', 'ß')}
    deacc = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    out.add(deacc)
    out = {re.sub(r'\s+', ' ', v).strip() for v in out}
    return [v for v in out if v]

def extract_candidates(text: str) -> list[str]:
    cands: set[str] = set()
    t = text or ""

    for m in ATTACHED.finditer(t):
        street, num = m.groups()
        cands.add(street if not num else f"{street} {num}")

    for m in SEPARATED.finditer(t):
        s = t[m.start():m.end()]
        cands.add(s.strip())

    for poi in poi_list:
        if re.search(rf"\b{re.escape(poi)}\b", t, re.IGNORECASE):
            cands.add(poi)

    if not cands:
        for chunk in re.split(r"[;,]", t):
            if re.search(SUFFIX_WORD, chunk, re.IGNORECASE):
                cands.add(chunk.strip())

    if not cands and t.strip():
        cands.add(t.strip())

    return [re.sub(r"\s+", " ", c).strip() for c in cands if c.strip()]

async def geocode_one(query: str) -> Optional[dict]:
    cand_list = variants(query)
    headers = {"User-Agent": "hamburg-transcription-geocoder/1.0 (you@example.com)"}

    for q in cand_list:
        params = {
            "q": f"{q}, Hamburg",
            "format": "json", "addressdetails": "1", "limit": "1",
            "viewbox": f"{HAMBURG_VIEWBOX['left']},{HAMBURG_VIEWBOX['top']},{HAMBURG_VIEWBOX['right']},{HAMBURG_VIEWBOX['bottom']}",
            "bounded": "1", "accept-language": "de", "countrycodes": "de",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                r = await client.get("https://nominatim.openstreetmap.org/search", params=params)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue

        if not data:
            continue

        x = data[0]
        lat, lon = x.get("lat"), x.get("lon")
        if lat is None or lon is None:
            bbox = x.get("boundingbox")
            if not bbox or len(bbox) != 4:
                continue
            lat = (float(bbox[0]) + float(bbox[1])) / 2.0
            lon = (float(bbox[2]) + float(bbox[3])) / 2.0
        else:
            lat, lon = float(lat), float(lon)

        addr = x.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village") or "Hamburg"
        street = addr.get("road")
        house  = addr.get("house_number")
        parts = []
        if street:
            parts.append(f"{street}{(' ' + house) if house else ''}")
        if addr.get("postcode"):
            parts.append(addr["postcode"])
        if city:
            parts.append(city)
        label = ", ".join(parts) if parts else x.get("display_name")

        return {
            "label": label, "lat": lat, "lng": lon, "source": "nominatim",
            "bbox": x.get("boundingbox"), "raw_address": addr, "q_used": q,
        }
    return None

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

# --- delete audio files referenced by old records ---
def delete_old_records(records):
    for record in records:
        # expected tuple: (id, inputpath, outputpath)
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
