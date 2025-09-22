# backend/api_server.py

import os, re, glob, uuid, subprocess, traceback
from typing import List, Set, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

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

        wav_name = f"{base}_{unique_id}.wav"
        wav_path = os.path.join(UPLOAD_DIR, wav_name)
        convert_webm_to_wav(webm_path, wav_path)
        os.remove(webm_path)

        run(["sh", "pretrained.sh", wav_name], cwd=BASE_DIR)

        files = glob.glob(os.path.join(OUTPUT_DIR, "*.json"))
        if not files:
            raise RuntimeError(f"No transcription JSON produced in {OUTPUT_DIR}")
        latest = max(files, key=os.path.getmtime)
        with open(latest, "r", encoding="utf-8") as f:
            transcription_data = f.read()

        return JSONResponse(content={"transcription": transcription_data})

    except Exception as e:
        print("UPLOAD ERROR:", e, "\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Geocoding ----------
HAMBURG_VIEWBOX = dict(left=8.4, top=53.95, right=10.5, bottom=53.3)

poi_list = [
    "Elbphilharmonie", "Miniatur Wunderland", "HafenCity", "Landungsbrücken",
    "Schanzenviertel", "St. Pauli", "Reeperbahn", "Planten un Blomen", "Altona",
    "Hauptbahnhof", "Dammtor", "Jungfernstieg", "Binnenalster", "Außenalster",
    "Rathausmarkt", "Speicherstadt", "Fischmarkt", "Eppendorf", "Winterhude",
]

street_regex = re.compile(
    r"\b([A-ZÄÖÜ][a-zäöüß]+(?:[ -][A-ZÄÖÜ][a-zäöüß]+)*\s"
    r"(?:Straße|Str\.|Weg|Allee|Platz|Ring|Damm|Gasse|Chaussee|Ufer))"
    r"\s*(\d+[a-zA-Z]?)?\b"
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


def prioritize(cands: Set[str]) -> List[str]:
    """Order candidates: house numbers > streets > POIs > generic Hamburg"""
    def score(c: str) -> int:
        if re.search(r"\d", c):  # has house number
            return 0
        if re.search(r"(Straße|Weg|Allee|Platz|Ring|Damm|Gasse|Ufer)", c):
            return 1
        if c in poi_list:
            return 2
        return 3
    return sorted(cands, key=score)


async def geocode_one(query: str) -> Optional[dict]:
    params = {
        "q": f"{query}, Hamburg",
        "format": "json",
        "addressdetails": "1",
        "limit": "1",
        "viewbox": f"{HAMBURG_VIEWBOX['left']},{HAMBURG_VIEWBOX['top']},"
                   f"{HAMBURG_VIEWBOX['right']},{HAMBURG_VIEWBOX['bottom']}",
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

    ordered = prioritize(candidates)
    markers, dbg = [], []
    for cand in ordered:
        try:
            hit = await geocode_one(cand)
            dbg.append({"candidate": cand, "hit": bool(hit)})
            if hit:
                markers.append(hit)
        except Exception as e:
            dbg.append({"candidate": cand, "error": str(e)})

    resp = {
        "markers": markers,
        "meta": {"candidates": ordered, "count": len(markers)},
    }
    if debug:
        resp["debug"] = dbg
    return resp

