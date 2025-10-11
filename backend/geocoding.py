import re
from typing import Optional
import unicodedata
import httpx


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
    if not q:
        return q
    s = q.strip()

    s = re.sub(r'\bStr\.\b', 'Straße', s, flags=re.IGNORECASE)
    s = re.sub(r'\bStrasse\b', 'Straße', s, flags=re.IGNORECASE)

    return s


def variants(q: str) -> list[str]:
    if not q:
        return []

    s = normalize_query(q)

    out = {s}

    out.add(s.replace('ß', 'ss'))
    out.add(s.replace('ss', 'ß'))

    deacc = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    out.add(deacc)

    # very common missing-'t' in '...stenstraße' (e.g. Kurfürsenstraße -> Kurfürstenstraße)
    out.add(re.sub(r'senstraße\b', 'stenstraße', s, flags=re.IGNORECASE))

    # collapse double spaces
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
            "q_used": q,
        }

    return None
