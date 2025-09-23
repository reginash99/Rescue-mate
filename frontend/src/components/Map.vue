<template>
  <div id="map" style="width:100%; height:100%;">
    <VMap
      ref="vmap"
      :center="center"
      :zoom="zoom"
      style="width:100%; height:100%;"
    >
      <VMapOsmTileLayer />
      <VMapZoomControl />
      <!-- no VMapMarker; we add markers via Leaflet API -->
    </VMap>
  </div>
</template>

<script setup>
import { VMap, VMapOsmTileLayer, VMapZoomControl } from 'vue-map-ui'
import { ref, watch, nextTick, onMounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Ensure Leaflet default marker icons resolve under Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl:       new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

const props = defineProps({
  // [{ lat: number, lng: number, label?: string }]
  markers: { type: Array, default: () => [] },
})

const center = ref([53.551086, 9.993682]) // Hamburg fallback
const zoom   = ref(12)

const vmap   = ref(null)   // <VMap> ref
const mapRef = ref(null)   // Leaflet map instance
let markersLayer = null    // L.LayerGroup for pins

onMounted(async () => {
  await nextTick()
  mapRef.value = vmap.value?.leafletObject || vmap.value?.map || null
  if (!mapRef.value) {
    // try once more on next tick (some builds expose it slightly later)
    setTimeout(() => {
      mapRef.value = vmap.value?.leafletObject || vmap.value?.map || null
      if (!mapRef.value) return
      markersLayer = L.layerGroup().addTo(mapRef.value)
      renderMarkersAndFit()
    }, 0)
  } else {
    markersLayer = L.layerGroup().addTo(mapRef.value)
    renderMarkersAndFit()
  }
})

// Re-render markers + fit whenever data changes
watch(
  () => props.markers,
  async () => {
    if (!mapRef.value || !markersLayer) return
    await nextTick()
    renderMarkersAndFit()
  },
  { deep: true }
)

function renderMarkersAndFit() {
  markersLayer.clearLayers()

  const ms = (props.markers || []).filter(m =>
    typeof m?.lat === 'number' && typeof m?.lng === 'number'
  )
  if (!ms.length) return

  const latlngs = []

  for (const m of ms) {
    const ll = [m.lat, m.lng]
    latlngs.push(ll)

    const label = String(m?.label ?? '').trim()
    const marker = L.marker(ll)

    // Hover tooltip (sticky so it follows the cursor); Popup on click (sticky)
    if (label) {
      marker
        .bindTooltip(label, {
          direction: 'top',
          sticky: true,
          opacity: 0.95,
          interactive: true,
        })
        .bindPopup(`<strong>${escapeHtml(label)}</strong>`)
      // Force visibility on interactions (some UIs suppress default behavior)
      marker.on('mouseover', () => marker.openTooltip())
      marker.on('mouseout',  () => marker.closeTooltip())
      marker.on('click',     () => marker.openPopup())
    }

    marker.addTo(markersLayer)
  }

  // Auto-fit to all markers (zoom out if far apart, in if close)
  const bounds = L.latLngBounds(latlngs)
  if (latlngs.length === 1) {
    mapRef.value.setView(latlngs[0], Math.min(mapRef.value.getMaxZoom?.() || 18, 16))
  } else {
    mapRef.value.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 })
  }
}

// tiny helper to avoid HTML injection
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]))
}
</script>