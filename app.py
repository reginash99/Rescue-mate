from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import whisper
import tempfile, os, re, requests

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # add others as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper once
model = whisper.load_model("base")

# ---- Geo utils ----
def geocode_feature(name, lat, lng, desc=None, id_=None):
    return {
        "type": "Feature",
        "properties": {"id": id_, "name": name, "desc": desc},
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
    }

def search_nominatim(query, bbox=(9.7, 53.7, 10.3, 53.35), bounded=True):
    """
    Hamburg-biased search. bbox = (left, top, right, bottom) in lon/lat.
    If bounded=True, results are restricted to the viewbox.
    """
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "viewbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "bounded": 1 if bounded else 0,
    }
    headers = {"User-Agent": "transcribe-map-app/1.0"}
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params=params, headers=headers, timeout=8)
    r.raise_for_status()
    results = r.json()
    if not results:
        return None
    best = results[0]
    lat = float(best["lat"]); lng = float(best["lon"])
    return geocode_feature(best.get("display_name", query), lat, lng, desc=best.get("display_name"))

def extract_place_queries(text: str, city_hint="Hamburg") -> list[str]:
    """
    Quick-and-dirty German pattern for things like:
      'McDonalds in der ABC-Straße', 'Rewe am Jungfernstieg', etc.
    Falls back to whole text + city.
    """
    street_words = r"(straße|str\.|weg|platz|allee|chaussee|ufer|damm|markt|chaussee)"
    pattern = re.compile(
        rf"\b(.+?)\s+(?:in der|am|an der|im|in|auf dem)\s+([A-ZÄÖÜ][\wÄÖÜäöüß\- ]*{street_words})\b",
        re.IGNORECASE
    )
    queries = []
    for m in pattern.finditer(text):
        brand = m.group(1).strip(' "\'.:,;-').split()[:5]   # keep it short-ish
        brand = " ".join(brand)
        street = m.group(2).strip()
        queries.append(f"{brand}, {street}, {city_hint}")

    # also try a simple brand + city if there’s a clear brand word
    brand_match = re.search(r"\b(McDonald'?s|Burger King|Rewe|Lidl|Aldi|Edeka|Subway|Starbucks|IKEA)\b", text, re.I)
    if brand_match:
        queries.append(f"{brand_match.group(0)}, {city_hint}")

    if not queries:
        queries = [f"{text.strip()}, {city_hint}"]

    # dedupe preserve order and limit
    seen = set(); uniq = []
    for q in queries:
        k = q.lower()
        if k not in seen:
            seen.add(k); uniq.append(q)
    return uniq[:5]

# ---- API ----
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "")[1] or ".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        result = model.transcribe(tmp_path)
        text = (result.get("text") or "").strip()

        queries = extract_place_queries(text, city_hint="Hamburg")

        features = []
        for i, q in enumerate(queries, 1):
            f = search_nominatim(q, bounded=True)   # set to False if you want “Hamburg-first, but allow outside”
            if f:
                f["properties"]["id"] = i
                features.append(f)

        return {
            "text": text,
            "locations": {"type": "FeatureCollection", "features": features}
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except Exception:
                pass
