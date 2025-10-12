const API = '/api' 

export async function geocodeTranscription(text) {
  const res = await fetch(`${API}/geocode`, { // <- relative path
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error(`Geocode failed: ${res.status}`)
  return res.json()
}


