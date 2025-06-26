import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'

//necessary for Map UI
import 'leaflet/dist/leaflet.css';
import 'vue-map-ui/dist/normalize.css';
import 'vue-map-ui/dist/style.css';
import 'vue-map-ui/dist/theme-all.css';


createApp(App).mount('#app')
