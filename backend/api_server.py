import os, re, glob, uuid, subprocess, traceback
from typing import List, Set, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import datetime
import json
from db import insert_record, delete_records, select_records, get_id, get_latest_id, select_record,create_new_record, add_audio_path
import dotenv
import unicodedata

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



dotenv.load_dotenv()

app = FastAPI()


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


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
        )
    return p


def convert_webm_to_wav(webm_path, wav_path):
    run(["ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", wav_path])



# --- Routes (after app exists) ---
@app.post("/transcribe-audio")
@app.post("/transcribe-audio/")
async def upload_audio(file: UploadFile = File(...)):
    try:
        unique_id = uuid.uuid4().hex[:8]
        base, ext = os.path.splitext(file.filename or "audio.webm")
        ext = ext or ".webm"
        webm_name = f"{base}_{unique_id}{ext}"
        webm_path = os.path.join(UPLOAD_DIR, webm_name)
        unique_filename = f"{base}_{unique_id}{ext}"
        file_location = os.path.join(UPLOAD_DIR, unique_filename)

        with open(webm_path, "wb") as f:
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

        # Update environment variables for subprocess
        env = os.environ.copy()
        env.update({
            "INPUT_AUDIO_DIR": UPLOAD_DIR,
            "OUTPUT_AUDIO_DIR": OUTPUT_AUDIO_DIR
        })

        subprocess.run([
            "sh", "pretrained.sh", wav_filename, current_id, UPLOAD_DIR, OUTPUT_AUDIO_DIR
        ], cwd=backend_dir, check=True, env=env)

     
        # delete all records older that 24 hours
        old_records = delete_records()
        delete_old_records(old_records)
        
        json_data = select_record(current_id)
        print(json_data)

        return JSONResponse(content={"transcription": json_data})
    except Exception as e:
        print("UPLOAD ERROR:", e, "\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/get-history/")
async def get_history(): 

    # delete all records older that 24 hours
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
street_regex = re.compile(
    r"\b([A-ZÄÖÜ][a-zäöüß]+(?:[ -][A-ZÄÖÜ][a-zäöüß]+)*\s(?:Straße|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer))\s*(\d+[a-zA-Z]?)?\b"
)
suffixless_number_regex = re.compile(
    r"\b([A-ZÄÖÜ][\wÄÖÜäöüß]+(?:[ -][A-ZÄÖÜ][\wÄÖÜäöüß]+){0,3})\s+(\d+[a-zA-Z]?)\b"
)
plz_regex = re.compile(r"\b(20\d{3}|21\d{3}|22\d{3})\s*Hamburg\b", re.I)

def extract_candidates(text: str) -> List[str]:
    if not text:
        return []
    cands: Set[str] = set()

    if re.search(r"\bHamburg\b", text, re.I):
        cands.add("Hamburg")
    for m in street_regex.finditer(text):
        street = " ".join(filter(None, [m.group(1), m.group(2)]))
        cands.add(street)
    for m in suffixless_number_regex.finditer(text):
        name = m.group(1)
        cands.add(f"{name} {m.group(2)}")
    for poi in poi_list:
        if re.search(rf"\b{re.escape(poi)}\b", text, re.I):
            cands.add(poi)
    m = plz_regex.search(text)
    if m:
        cands.add(m.group(0))
    return list(cands)

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
            "q_used": q,     # optional: helps debug which variant matched
        }

    return None

SUFFIX = r"(Stra(?:ße|sse)|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer)"

street_with_optional_number = re.compile(
    rf"\b([A-ZÄÖÜ][\wÄÖÜäöüß\-]+(?:[ -][A-ZÄÖÜ][\wÄÖÜäöüß\-]+)*)\s{SUFFIX}(?:\s+(\d+[a-zA-Z]?))?\b",
    re.IGNORECASE | re.UNICODE
)

def extract_candidates(text: str) -> list[str]:
    cands: set[str] = set()
    for m in street_with_optional_number.finditer(text or ""):
        name, suf, num = m.groups()
        street = f"{name} {suf}" + (f" {num}" if num else "")
        cands.add(street)
    # also split commas as last resort
    for chunk in re.split(r"[;,]", text or ""):
        if re.search(SUFFIX, chunk, re.I):
            cands.add(chunk.strip())
    return list(cands)


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
        for c in extract_candidates(t or ""):
            candidates.add(c)

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

# function to delete audio files older than 24 hours from records
def delete_old_records(records):
    for record in records:
        #0 id, 1 inputpath, 2 outputpath
        print("deleting files from record with id: ", record[0])

        print("deleting input audio file: ", record[1])
        try:
            os.remove(record[1])
        except Exception as e:
            print("could not delete input audio file: ", e)

        print("deleting output audio file: ", record[2])
        try:
            os.remove(record[2])
            
        except Exception as e:
            print("could not delete input audio file: ", e)

# @app.get("/get-audio/{filename}")
# async def get_audio(filename: str):
#     file_path = os.path.join(UPLOAD_DIR, filename)
#     if not os.path.exists(file_path):
#         return {"error": "File not found"}
#     return FileResponse(file_path)