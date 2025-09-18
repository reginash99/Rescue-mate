import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'

//necessary for Map UI
import 'leaflet/dist/leaflet.css';
import 'vue-map-ui/dist/normalize.css';
import 'vue-map-ui/dist/style.css';
import 'vue-map-ui/dist/theme-all.css';

//necessay for resizing components
// @ts-ignore
import VueDraggableResizable from 'vue-draggable-resizable'
import 'vue-draggable-resizable/style.css'

export default {
  components: { VueDraggableResizable }
}

createApp(App)
    .component("vue-draggable-resizable", VueDraggableResizable)
    .mount('#app');