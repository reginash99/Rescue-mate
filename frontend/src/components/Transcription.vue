<template>
  <div class="transcription-main">
    <h1>Transcription</h1>

    <div class="dev-panel">
      <h3>Manual transcription</h3>
      <textarea v-model="transcriptText" rows="5" class="dev-textarea"></textarea>
      <div class="dev-actions">
        <button class="btn" @click="geocodeTranscript">Geocode transcript (API)</button>
        <button class="btn outline" @click="useMock">Mock pins</button>
        <button class="btn outline" @click="clearMarkers">Clear</button>
      </div>
      <p class="hint">
        Geocodes using Nominatim with a Hamburg bounding box. Later you can switch to Mapbox/OpenCage or your own backend.
      </p>
    </div>

    <div class="transcription">
      <p v-if="lastText">Last text: {{ lastText }}</p>
      <p v-else>Transcribing...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMapStore } from '../stores/map'

const mapStore = useMapStore()
const transcriptText = ref('McDonalds in der ABC-Straße, dann Rewe am Jungfernstieg in Hamburg')
const lastText = ref('')

// ---------- Types & helpers ----------
type Feature = {
  type: 'Feature'
  properties: { id?: number; name?: string; desc?: string }
  geometry: { type: 'Point'; coordinates: [number, number] } // [lng, lat]
}
type FeatureCollection = { type: 'FeatureCollection'; features: Feature[] }

function toFeature(name: string, lng: number, lat: number, desc?: string): Feature {
  return { type: 'Feature', properties: { name, desc }, geometry: { type: 'Point', coordinates: [lng, lat] } }
}

function setFC(feats: Feature[]) {
  feats.forEach((f, i) => (f.properties.id = i + 1))
  mapStore.setFeatures({ type: 'FeatureCollection', features: feats } as any)
}

// Very small extractor for phrases like “X in der Y-Straße”, “Rewe am Jungfernstieg”
function extractQueries(text: string, city = 'Hamburg'): string[] {
  const queries: string[] = []
  const streetWords = /(straße|str\.|weg|platz|allee|ufer|damm|markt)/i
  const re = new RegExp(`\\b(.+?)\\s+(?:in der|am|an der|im|in)\\s+([A-ZÄÖÜ][\\wÄÖÜäöüß\\- ]*${streetWords.source})\\b`, 'gi')
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) {
    const brand = m[1].trim().replace(/^[ "'.,:;-]+|[ "'.,:;-]+$/g, '').split(/\s+/).slice(0, 5).join(' ')
    const street = m[2].trim()
    queries.push(`${brand}, ${street}, ${city}`)
  }
  // add a simple brand+city fallback
  const brand = /McDonald'?s|Burger King|Rewe|Lidl|Aldi|Edeka|Subway|Starbucks|IKEA/i.exec(text)?.[0]
  if (brand) queries.push(`${brand}, ${city}`)
  if (queries.length === 0) queries.push(`${text.trim()}, ${city}`)
  // dedupe
  const seen = new Set<string>(); const out: string[] = []
  for (const q of queries) { const k = q.toLowerCase(); if (!seen.has(k)) { seen.add(k); out.push(q) } }
  return out.slice(0, 5)
}

// ---------- API: Nominatim (no key) with Hamburg bias ----------
async function geocodeNominatim(query: string): Promise<Feature | null> {
  // Hamburg bounding box: left,top,right,bottom (lon/lat)
  const bbox = [9.7, 53.7, 10.3, 53.35]
  const params = new URLSearchParams({
    q: query,
    format: 'jsonv2',
    limit: '1',
    addressdetails: '0',
    viewbox: `${bbox[0]},${bbox[1]},${bbox[2]},${bbox[3]}`,
    bounded: '1'
  })
  const url = `https://nominatim.openstreetmap.org/search?${params.toString()}`
  const r = await fetch(url, { headers: { accept: 'application/json' } })
  if (!r.ok) return null
  const arr = await r.json()
  if (!Array.isArray(arr) || arr.length === 0) return null
  const best = arr[0]
  const lat = parseFloat(best.lat), lng = parseFloat(best.lon)
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null
  return toFeature(best.display_name ?? query, lng, lat, best.display_name)
}

// Optional: Mapbox (set VITE_MAPBOX_TOKEN in .env.local, and switch provider below)
const MAPBOX_TOKEN = (import.meta as any).env?.VITE_MAPBOX_TOKEN as string | undefined
async function geocodeMapbox(query: string): Promise<Feature | null> {
  if (!MAPBOX_TOKEN) return null
  const proximity = '9.9937,53.5511' // lng,lat (Hamburg center)
  const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?` +
              `access_token=${MAPBOX_TOKEN}&autocomplete=false&language=de&limit=1&types=poi,address&proximity=${proximity}`
  const r = await fetch(url)
  if (!r.ok) return null
  const js = await r.json()
  const f = js?.features?.[0]
  if (!f) return null
  const [lng, lat] = f.center
  return toFeature(f.text || query, lng, lat, f.place_name)
}

// ---------- Actions ----------
async function geocodeTranscript() {
  const text = transcriptText.value.trim()
  if (!text) return
  lastText.value = text

  const queries = extractQueries(text, 'Hamburg')
  console.log('[geocode] queries ->', queries)

  // Choose provider: try Mapbox first if token exists, else Nominatim
  const feats: Feature[] = []
  for (const q of queries) {
    let f: Feature | null = null
    if (MAPBOX_TOKEN) f = await geocodeMapbox(q)
    if (!f) f = await geocodeNominatim(q)
    if (f) feats.push(f)
  }
  console.log('[geocode] features ->', feats)
  setFC(feats)
}

// Fallback mock so you can still test quickly
function useMock() {
  setFC([
    toFeature('Rewe (Jungfernstieg)', 9.9916, 53.5537, 'Mock'),
    toFeature('McDonald’s (Dammtor?)', 9.9894, 53.5565, 'Mock')
  ])
  lastText.value = transcriptText.value
}

function clearMarkers() {
  setFC([])
}
</script>

<style scoped>
.transcription-main { display: flex; flex-direction: column; height: 100%; width: 100%; box-sizing: border-box; }
h1 { text-align: left; margin: 1% 0 0 2%; box-sizing: border-box; }
.transcription { flex: 1 1 0; display: flex; padding: 10px; font-size: large; background-color: #EEE; box-sizing: border-box; margin: 15px; }

.dev-panel { margin: 10px 15px 0 15px; padding: 12px; border: 1px dashed #bbb; border-radius: 6px; background: #fafafa; }
.dev-textarea { width: 100%; box-sizing: border-box; font-family: inherit; margin: 8px 0; }
.dev-actions { display: flex; gap: 8px; margin-top: 6px; }
.btn { padding: 6px 10px; border: 1px solid #333; background: #fff; cursor: pointer; border-radius: 4px; }
.btn.outline { background: transparent; }
.hint { font-size: 12px; color: #666; margin-top: 6px; }
</style>
