<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { VMap, VMapOsmTileLayer, VMapZoomControl, VMapMarker } from 'vue-map-ui'
import { useMapStore } from '../stores/map'

const store = useMapStore()

const center = ref<[number, number]>([53.551086, 9.993682]) // default Hamburg
const zoom = ref(12)

const markers = computed(() =>
  (store.features || []).map((f: any, i: number) => {
    const [lng, lat] = f.geometry.coordinates // GeoJSON = [lng, lat]
    return { id: f.properties?.id ?? i, lat, lng, name: f.properties?.name }
  })
)

watch(markers, (ms) => {
  if (ms.length) center.value = [ms[0].lat, ms[0].lng]   // recenter on first result
}, { immediate: true })
</script>

<template>
  <div style="width:100%; height:100%">
    <VMap :center="center" :zoom="zoom" style="width:100%; height:100%">
      <VMapOsmTileLayer />
      <VMapZoomControl />
      <VMapMarker v-for="m in markers" :key="m.id" :latlng="[m.lat, m.lng]" />
    </VMap>
  </div>
</template>
