# Rescue-mate

Naming Convention:
f = frontend
b = backend
f_component_something
b_component_something

## FRONTEND
# Map

For implementing the map we used Vue Map, a provided open-source UI Framework for vue.js based on Leaflet which is an open-source JavaScript library
for mobile-friendly interactive maps.

For installing this framework, execute the following command in the terminal: 

```
npm install vue-map-ui leaflet.
```

Then, import four css files in the main.ts file which are necessary for the correct rendering of the map:

```
import 'leaflet/dist/leaflet.css';
import 'vue-map-ui/dist/normalize.css';
import 'vue-map-ui/dist/style.css';
import 'vue-map-ui/dist/theme-all.css';
```
In the Map Component, add the following structure

```
<VMap  :center=center :zoom=zoom :id="VMap" :style="{width: '100%', height: '100%'}"
      <VMapOsmTileLayer />
      <VMapZoomControl />
      <VMapMarker :latlng=location />
</VMap>
```

Since our application concentrates on Hamburg, the map is centered per default around the Rathaus. 
Currently the geo data of the Hamburg Rathaus are used to display a marker in the map, demonstrating how it might look when geodata is extracted from the audio.

If no data was found, then no map but a notification will be displayed informing that no data was found.

