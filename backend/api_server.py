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

dotenv.load_dotenv()

UPLOAD_DIR = "./input_audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI()

# backend/api_server.py



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
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "input_audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_transcriptions")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# @app.get("/get-audio/{filename}")
# async def get_audio(filename: str):
#     file_path = os.path.join(UPLOAD_DIR, filename)
#     if not os.path.exists(file_path):
#         return {"error": "File not found"}
#     return FileResponse(file_path)