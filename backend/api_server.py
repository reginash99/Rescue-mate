from fastapi import FastAPI, UploadFile, File, HTTPException  # + HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import subprocess
import glob
import datetime
import uuid
from pydantic import BaseModel
from typing import List, Set, Optional
import httpx
import re

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

# ---------- Hamburg geocoding helpers ----------

HAMBURG_VIEWBOX = dict(left=8.4, top=53.95, right=10.5, bottom=53.3)

# Basic German street/POI extraction. Improve later if needed.
poi_list = [
    'Elbphilharmonie','Miniatur Wunderland','HafenCity','Landungsbrücken',
    'Schanzenviertel','St. Pauli','Reeperbahn','Planten un Blomen','Altona',
    'Hauptbahnhof','Dammtor','Jungfernstieg','Binnenalster','Außenalster',
    'Rathausmarkt','Speicherstadt','Fischmarkt','Eppendorf','Winterhude'
]

street_regex = re.compile(
    r'\b([A-ZÄÖÜ][a-zäöüß]+(?:[ -][A-ZÄÖÜ][a-zäöüß]+)*\s(?:Straße|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer))\s*(\d+[a-zA-Z]?)?\b'
)
plz_regex = re.compile(r'\b(20\d{3}|21\d{3}|22\d{3})\s*Hamburg\b', re.I)

def extract_candidates(text: str) -> List[str]:
    if not text:
        return []
    cands: Set[str] = set()

    if re.search(r'\bHamburg\b', text, re.I):
        cands.add('Hamburg')

    for m in street_regex.finditer(text):
        street = ' '.join(filter(None, [m.group(1), m.group(2)]))
        cands.add(street)

    for poi in poi_list:
        if re.search(rf'\b{re.escape(poi)}\b', text, re.I):
            cands.add(poi)

    m = plz_regex.search(text)
    if m:
        cands.add(m.group(0))

    return list(cands)

async def geocode_one(query: str) -> Optional[dict]:
    params = {
        "q": f"{query}, Hamburg",
        "format": "json",
        "addressdetails": "1",
        "limit": "1",
        "viewbox": f"{HAMBURG_VIEWBOX['left']},{HAMBURG_VIEWBOX['top']},{HAMBURG_VIEWBOX['right']},{HAMBURG_VIEWBOX['bottom']}",
        "bounded": "1",
    }
    headers = {"User-Agent": "hamburg-transcription-geocoder/1.0 (your-email@example.com)"}
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        r = await client.get("https://nominatim.openstreetmap.org/search", params=params)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    x = data[0]
    return {
        "label": x.get("display_name"),
        "lat": float(x["lat"]),
        "lng": float(x["lon"]),
        "source": "nominatim",
        "bbox": x.get("boundingbox"),
    }

class GeocodeIn(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None

@app.post("/geocode")
async def geocode(payload: GeocodeIn):
    texts = payload.texts if payload.texts else ([payload.text] if payload.text else [])
    if not texts:
        raise HTTPException(status_code=400, detail="Provide `text` or `texts`.")

    candidates: Set[str] = set()
    for t in texts:
        for c in extract_candidates(t or ""):
            candidates.add(c)

    markers: List[dict] = []
    for cand in candidates:
        try:
            hit = await geocode_one(cand)
            if hit:
                markers.append(hit)
        except Exception:
            # swallow individual failures (you can log if you want)
            pass

    return {"markers": markers, "meta": {"candidates": list(candidates), "count": len(markers)}}
