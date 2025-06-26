<template>
  <div id="map" :style="{width: '100%', height: '100%'}">
    <VMap  :center=center :zoom=zoom :id="VMap" :style="{width: '100%', height: '100%'}" v-if="AdressFound"> <!--:style="{width: clientWidth + 'px', height: clientHeight + 'px'}"-->
      <VMapOsmTileLayer />
      <VMapZoomControl />
      <!--<VMapAttributionControl />-->
      <VMapMarker :latlng=location />
  </VMap>
  <div v-else id="map_not_found">
    <p> Adress not available</p>
  </div>
  </div>
</template>

<script setup>

import { VMap,VMapOsmTileLayer,VMapZoomControl,VMapMarker} from 'vue-map-ui'
import { ref } from 'vue';
import L from 'leaflet';

const AdressFound = ref(true)
const clientWidth = ref(800).value;
const clientHeight = ref(800).value;
const coord_Hamburg = [53.551086, 9.993682]; // Hamburg Rathaus

const center = ref(coord_Hamburg);
const zoom = ref(12);
const bounds = ref([10,10],[20,20]);

const location = [53.551086, 9.993682];

console.log(clientHeight)
console.log(clientWidth)

</script>

<style>
#map_not_found {
  width:100%;
  height: 100%;
  background-color: grey;
  opacity: 0.1;
}
#map_not_found p {
  position: relative;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: black;
  font-size: 30px;
  text-align: center;
  z-index: 2;
  opacity: 1;
}
</style>
