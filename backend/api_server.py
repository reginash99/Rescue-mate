import os, re, uuid, subprocess
from typing import List, Set, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
from db import delete_records, select_records, get_latest_id, create_new_record, add_audio_path, select_transcriptions, select_intermediate_result
import dotenv
import unicodedata
import asyncio
from fastapi import Request
import datetime

dotenv.load_dotenv()

app = FastAPI()
logs_store = {}
pending_responses = {}


# --- create app FIRST ---
app = FastAPI()

# --- CORS (optional if you proxy through Vite) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths & helpers ---
# Base directory for backend files
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Directories can be overridden with environment variables when deploying to a server
UPLOAD_DIR = os.getenv("INPUT_AUDIO_DIR", os.path.join(BASE_DIR, "input_audio"))
OUTPUT_AUDIO_DIR = os.getenv("OUTPUT_AUDIO_DIR", os.path.join(BASE_DIR, "output_audio"))
OUTPUT_TRANSCRIPT_DIR = os.getenv("OUTPUT_TRANSCRIPT_DIR", os.path.join(BASE_DIR, "output_transcriptions"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)


def normalize_query(q: str) -> str:
    if not q:
        return q
    s = q.strip()

    # unify common suffix spellings
    s = re.sub(r'\bStr\.\b', 'Straße', s, flags=re.IGNORECASE)
    s = re.sub(r'\bStrasse\b', 'Straße', s, flags=re.IGNORECASE)

    # two-way ß/ss variants
    return s

def variants(q: str) -> list[str]:
    """Return a few spelling variants to try with Nominatim."""
    if not q:
        return []

    s = normalize_query(q)

    out = {s}

    # ß <-> ss
    out.add(s.replace('ß', 'ss'))
    out.add(s.replace('ss', 'ß'))

    # de-accent version (ä->a etc.) for lenient search
    deacc = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    out.add(deacc)

    # very common missing-'t' in '...stenstraße' (e.g. Kurfürsenstraße -> Kurfürstenstraße)
    out.add(re.sub(r'senstraße\b', 'stenstraße', s, flags=re.IGNORECASE))

    # collapse double spaces
    out = {re.sub(r'\s+', ' ', v).strip() for v in out}

    # keep short non-empty
    return [v for v in out if v]


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
        )
    return p

def convert_webm_to_wav(webm_path, wav_path):
    run(["ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", wav_path])



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

        # Convert to WAV
        wav_filename = f"{base}_{unique_id}.wav"
        wav_location = os.path.join(UPLOAD_DIR, wav_filename)
        convert_webm_to_wav(webm_path, wav_location)
        os.remove(webm_path)

        # DB: create new record
        create_new_record()
        current_id = str(get_latest_id())
        add_audio_path(current_id, wav_location, 0)

        # Update environment variables for subprocess
        env = os.environ.copy()
        env.update({
            "INPUT_AUDIO_DIR": UPLOAD_DIR,
            "OUTPUT_AUDIO_DIR": OUTPUT_AUDIO_DIR
        })

        # Launch inference
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

        # delete all records older that 24 hours
        old_records = delete_records()
        delete_old_records(old_records)
        

        # Suspend until inference notifies us
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
    
    # Store in DB or just push into memory
    #add_log_message(current_id, message)


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
    # delete all records older than 24 hours
    old_records = delete_records()
    delete_old_records(old_records)
    records = select_records()
    return JSONResponse(content={"history": records})

# ---------- Geocoding ----------
HAMBURG_VIEWBOX = dict(left=8.4, top=53.95, right=10.5, bottom=53.3)

poi_list = [
    "Elbphilharmonie","Miniatur Wunderland","HafenCity","Landungsbrücken",
    "Schanzenviertel","St. Pauli","Reeperbahn","Planten un Blomen","Altona",
    "Hauptbahnhof","Dammtor","Jungfernstieg","Binnenalster","Außenalster",
    "Rathausmarkt","Speicherstadt","Fischmarkt","Eppendorf","Winterhude",
]

# Suffixes we care about (also handle "...stieg")
SUFFIX_WORD = r"(?:Stra(?:ße|sse)|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer|Stieg)"

# 1) Attached form: "Kurfürstenstraße 29", "Jungfernstieg 12", "Jungfernstieg"
ATTACHED = re.compile(
    rf"\b([A-ZÄÖÜ][\wÄÖÜäöüß\-]*(?:{SUFFIX_WORD}))(?:\s+(\d+[a-zA-Z]?))?\b",
    re.IGNORECASE | re.UNICODE,
)

# 2) Separated form: "Kurfürsten Straße 29"
SEPARATED = re.compile(
    rf"\b([A-ZÄÖÜ][\wÄÖÜäöüß\-]+(?:[ -][A-ZÄÖÜ][\wÄÖÜäöüß\-]+)*)\s{SUFFIX_WORD}(?:\s+(\d+[a-zA-Z]?))?\b",
    re.IGNORECASE | re.UNICODE,
)

def extract_candidates(text: str) -> list[str]:
    cands: set[str] = set()
    t = text or ""

    # streets: attached suffix
    for m in ATTACHED.finditer(t):
        street, num = m.groups()
        cands.add(street if not num else f"{street} {num}")

    # streets: separated suffix (reconstruct exact surface form)
    for m in SEPARATED.finditer(t):
        s = t[m.start():m.end()]
        cands.add(s.strip())

    # POIs
    for poi in poi_list:
        if re.search(rf"\b{re.escape(poi)}\b", t, re.IGNORECASE):
            cands.add(poi)

    # last resort: comma/semicolon chunks with a suffix token somewhere
    if not cands:
        for chunk in re.split(r"[;,]", t):
            if re.search(SUFFIX_WORD, chunk, re.IGNORECASE):
                cands.add(chunk.strip())

    # absolute fallback: try the whole string (Nominatim is tolerant)
    if not cands and t.strip():
        cands.add(t.strip())

    # collapse spaces
    return [re.sub(r"\s+", " ", c).strip() for c in cands if c.strip()]

async def geocode_one(query: str) -> Optional[dict]:
    cand_list = variants(query)
    headers = {"User-Agent": "hamburg-transcription-geocoder/1.0 (you@example.com)"}

    for q in cand_list:
        params = {
            "q": f"{q}, Hamburg",
            "format": "json",
            "addressdetails": "1",
            "limit": "1",
            "viewbox": f"{HAMBURG_VIEWBOX['left']},{HAMBURG_VIEWBOX['top']},"
                       f"{HAMBURG_VIEWBOX['right']},{HAMBURG_VIEWBOX['bottom']}",
            "bounded": "1",
            "accept-language": "de",
            "countrycodes": "de",
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

        # pretty label
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
            "label": label,
            "lat": lat,
            "lng": lon,
            "source": "nominatim",
            "bbox": x.get("boundingbox"),
            "raw_address": addr,
            "q_used": q,  # helps debug which variant matched
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
