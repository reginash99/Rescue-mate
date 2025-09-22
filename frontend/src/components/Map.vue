<template>
  <div id="map" :style="{ width: '100%', height: '100%' }">
    <VMap
      :center="center"
      :zoom="zoom"
      :style="{ width: '100%', height: '100%' }"
      @ready="onMapReady"
    >
      <VMapOsmTileLayer />
      <VMapZoomControl />

      <!-- Render markers if any -->
      <VMapMarker
        v-for="(m, i) in markers"
        :key="i"
        :latlng="[m.lat, m.lng]"
        :tooltip="m.label"
      />
    </VMap>

    <!-- Overlay notice if no markers -->
<!--     <div v-if="!markers.length" id="map_not_found">
      <p>Address not available</p>
    </div> -->
  </div>
</template>

<script setup>
import { VMap, VMapOsmTileLayer, VMapZoomControl, VMapMarker } from 'vue-map-ui'
import { watch, ref } from 'vue'

const props = defineProps({
  markers: { type: Array, default: () => [] },
});

const center = ref([53.551086, 9.993682]) // Hamburg Rathaus default
const zoom = ref(12)

const mapRef = ref(null)

function onMapReady(mapInstance) {
  mapRef.value = mapInstance?.leafletObject || mapInstance
  maybeFitBounds()
}

watch(() => props.markers, () => {
  maybeFitBounds()
}, { deep: true })

function maybeFitBounds() {
  if (!mapRef.value || !props.markers?.length) return
  const L = window.L
  const bounds = props.markers.reduce((acc, m) => {
    const latlng = [m.lat, m.lng]
    if (!acc) return L.latLngBounds([latlng, latlng])
    acc.extend(latlng)
    return acc
  }, null)
  if (bounds) {
    mapRef.value.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 })
  }
}
</script>

<style>
#map_not_found {
  position: absolute;
  top: 0;
  left: 0;
  width:100%;
  height:100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(128, 128, 128, 0.2);
  pointer-events: none;
}
#map_not_found p {
  font-size: 24px;
  color: black;
}
</style>
