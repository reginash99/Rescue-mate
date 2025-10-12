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
    </VMap>
  </div>
</template>

<script setup>
import { VMap, VMapOsmTileLayer, VMapZoomControl } from 'vue-map-ui'
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default icon paths under Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl:       new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

const props = defineProps({
  // must be [{ lat:number, lng:number, label?:string }]
  markers: { type: Array, default: () => [] },
})

const center = ref([53.551086, 9.993682]) // Hamburg default
const zoom   = ref(12)

const vmap   = ref(null)   // <VMap> ref
const mapRef = ref(null)   // Leaflet map instance
let markersLayer = null
let ro = null // ResizeObserver

function coerceMarkers(arr) {
  return (arr || [])
    .map(m => ({ ...m, lat: Number(m.lat), lng: Number(m.lng) }))
    .filter(m => Number.isFinite(m.lat) && Number.isFinite(m.lng))
}

async function renderMarkersAndFit() {
  if (!mapRef.value || !markersLayer) return

  const ms = coerceMarkers(props.markers)
  console.log('[Map.vue] incoming markers:', ms)

  markersLayer.clearLayers()
  if (!ms.length) return

  const latlngs = []

  for (const m of ms) {
    const ll = [m.lat, m.lng]
    latlngs.push(ll)
    const label = (m.label ?? '').toString().trim()
    const marker = L.marker(ll, { zIndexOffset: 1000 })
    if (label) {
      marker.bindTooltip(label, { direction: 'top', sticky: true, opacity: 0.95 })
            .bindPopup(label)
    }
    marker.addTo(markersLayer)
  }

  // recalc layout then fit
  mapRef.value.invalidateSize(false)
  fitNow(latlngs)
  setTimeout(() => fitNow(latlngs), 0)
}

function fitNow(latlngs) {
  if (!latlngs.length) return
  if (latlngs.length === 1) {
    mapRef.value.setView(latlngs[0], Math.min(mapRef.value.getMaxZoom?.() || 18, 16))
  } else {
    mapRef.value.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40], maxZoom: 16 })
  }
}

onMounted(async () => {
  await nextTick()
  mapRef.value = vmap.value?.leafletObject || vmap.value?.map || null

  if (!mapRef.value) {
    // vue-map-ui sometimes exposes the Leaflet map one tick later
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

  // If parent size changes (tabs/panels), keep map in sync
  const el = document.getElementById('map')
  if (el && 'ResizeObserver' in window) {
    ro = new ResizeObserver(() => {
      if (mapRef.value) {
        mapRef.value.invalidateSize(false)
        renderMarkersAndFit()
      }
    })
    ro.observe(el)
  }
})

// Re-render on prop change (immediate so first batch shows)
watch(
  () => props.markers,
  async () => {
    if (!mapRef.value || !markersLayer) return
    await nextTick()
    renderMarkersAndFit()
  },
  { deep: true, immediate: true }
)

onBeforeUnmount(() => {
  if (ro) ro.disconnect()
})
</script>
