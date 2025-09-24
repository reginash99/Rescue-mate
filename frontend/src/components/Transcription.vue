<template>
  <div class="transcription-main" :class="{ 'is-busy': status }">
    <h1>Transcription</h1>
    <button class="btn-info" @click="openModal">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-info-lg" viewBox="0 0 16 16">
        <path d="m9.708 6.075-3.024.379-.108.502.595.108c.387.093.464.232.38.619l-.975 4.577c-.255 1.183.14 1.74 1.067 1.74.72 0 1.554-.332 1.933-.789l.116-.549c-.263.232-.65.325-.905.325-.363 0-.494-.255-.402-.704zm.091-2.755a1.32 1.32 0 1 1-2.64 0 1.32 1.32 0 0 1 2.64 0"/>
        </svg>
    </button>

<div class="transcription">
  <div :class="['transcription-text', { shrunk: panelOpen }]">
    <div v-if="props.data?.transcription">
      <p>{{ props.data.transcription ?? "…" }}</p>

      <small v-if="props.data.timestamp">
        {{ props.data.timestamp }}
      </small>
  </div>
  
  <div v-else>
    <p><i>Press the record button to transcribe your audio</i></p>
  </div>
  <div v-if="status" class="overlay">
    <div class="spinner"></div>
    <div class="overlay-text">Processing…</div>
  </div>
</div>

<div class="side-panel" v-if="panelOpen">
  <div v-if="updates.length > 0">
    <div v-for="(u, i) in updates" :key="i">
      <p>{{ u.stage }}: {{ u.text }}</p>
    </div>
  </div>
  <div v-else>
    <p><i>No updates available</i></p>
  </div>
</div>

  
      <button class="btn floating-btn" @click="panelOpen = !panelOpen">
        <img src="./media/notification.png"></img>
        <span v-if="!panelOpen">!</span>
      </button>
    </div>
    <!-- <div class="updates" v-if="panelOpen">
      <p>Showing update for transcript...</p>
    </div> -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <button class="modal-close" @click="closeModal">×</button>
        <h4>Information</h4>
          <p>The transcription displayed initially is raw. After further processing, the transcription will be updated if its quality is better than the raw transcription. If an update is available, the bell button in the bottom right corner of the transcription will show a red alert bubble and can be clicked to display the updated transcription.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { geocodeTranscription } from '@/composables/useGeocode.js'

const props = defineProps({
  data: Object, // contains { transcription, id, status, timestamp }
  status: { type: Boolean, default: false },
})
const emit = defineEmits(['markers-found'])

const panelOpen = ref(false)
const showModal = ref(false)
const isGeocoding = ref(false)
const markers = ref([])
const updates = ref([]) // array of stage transcripts
let pollInterval = null

// Watch raw transcription for geocoding
watch(() => props.data?.transcription, async (newVal) => {
const text = typeof newVal === "string" ? newVal : newVal?.transcription
  markers.value = []
  if (!text || !text.trim()) {
    emit('markers-found', [])
    return
  }
  try {
    isGeocoding.value = true
    const { markers: m } = await geocodeTranscription(text)
    markers.value = m || []
    emit('markers-found', markers.value)
  } catch (e) {
    console.error(e)
    emit('markers-found', [])
  } finally {
    isGeocoding.value = false
  }
})

// Poll backend for updates
function startPolling(id) {
  stopPolling()
  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/get-intermediate-transcript/${id}`)
      if (!res.ok) return
      const json = await res.json()
      updates.value = json.transcripts || []
    } catch (e) {
      console.error("Polling error:", e)
    }
  }, 3000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// When we get a new ID from backend, start polling
watch(() => props.data?.id, (newId) => {
  if (newId) startPolling(newId)
  else stopPolling()
})

onUnmounted(() => stopPolling())

function openModal() { showModal.value = true }
function closeModal() { showModal.value = false }
</script>



<style scoped>

.transcription-main {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  position: relative;
}

.transcription-main h1 {
  text-align: center;
  margin: 1% 0 0 2%;
}

.transcription {
  position: relative;
  flex: 1 1 0;
  display: flex;
  padding: 15px;
  font-size: x-large;
  min-height: 300px;
  height: 100%;
  background-color: var(--secondary-background);
  margin: 15px;
  border-radius: 15px;
  box-shadow: 0 8px 8px var(--shadow-color);
  overflow: auto;
  align-items: stretch;
}

.transcription.shrunk {
  flex: 0 1 50%;
  max-width: 50%;
}

.transcription-text {
  color: var(--color-text);
  width: 100%;
  max-width: 100%;
  z-index: 1;
  flex: 1;
}

.transcription-text.shrunk {
  width: 50%;
  max-width: 50%;
}

/* Floating Button */
.floating-btn {
  position: absolute;
  bottom: 10px;
  right: 10px;
  width: auto;
  height: 50px;
  border-radius: 50%;
  background-color: #AAD2DE;
  color: white;
  border: none;
  box-shadow: 0 4px 16px var(--shadow-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  z-index: 10;
  transition: background 0.2s, box-shadow 0.2s;
  text-decoration: none;
}

.floating-btn:hover {
  background-color: rgb(255, 255, 255);
  box-shadow: 0 8px 32px var(--shadow-color);
}

.floating-btn span {
  position: absolute;
  top: -3px;
  right: 0px;
  background: #eb0010;
  font-size: 14px;
  font-weight: bold;
  width: 20px;
  height: 20px;
  display: flex;
  justify-content: center;
  border-radius: 50%;
}

.floating-btn img {
  width: 27px;
  height: 27px;
}

/* Updates caption */
.updates {
  position: relative;
  left: 20px;
  margin-top: -5px;
  margin-bottom: -12px;
  opacity: 0;
  animation: fadeInCaption 0.5s cubic-bezier(.77,0,.18,1) forwards;
}

@keyframes fadeInCaption {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}

/* Processing Buffer */
.is-busy {
  filter: grayscale(1);
  opacity: 0.5;
  pointer-events: none; /* block interactions */
  color: var(--color-text-2) !important;
}

.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  backdrop-filter: blur(2px);
  color: var(--color-text-2) !important;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0,0,0,0.2);
  border-top-color: rgba(0,0,0,0.6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  color: var(--color-text-2) !important;
  margin-bottom: 8px;
}

.overlay-text {
  font-size: 0.9rem;
  color: var(--color-text-2) !important;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}


/* Side Panel */
.side-panel {
  top: 0;
  right: 0;
  width: 50%;
  min-height: 100%;
  position: absolute;
  border-radius: 0 15px 15px 0;
  background-color: var(--ternary-background);
  transition: opacity 0.3s;
  color: var(--color-text-2) !important;
  overflow-y: auto;
  padding: 15px;
  flex: 1;
}

/* Info button */
.btn-info {
  position: absolute;
  top: 20px;
  right: 25px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: var(--secondary-background);
  color: var(--color-text);
  border: none;
  box-shadow: 0 4px 16px var(--shadow-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  cursor: pointer;
  z-index: 10;
  transition: background 0.2s, box-shadow 0.2s;
}

/* Modal View */

.modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(190, 188, 188, 0.288);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
}

.modal-content {
    overflow-y: auto;
    overflow-x: auto;
    background: var(--color-background);
    border-radius: 12px;
    padding: 28px 24px 24px 24px;
    width: auto;
    min-width: 250px;
    max-width: 500px;
    height: auto;
    max-height: 400px;
    min-height: 250px;
    box-shadow: 0 8px 32px var(--shadow-color);
    position: relative;
    font-size: larger;
}

.modal-close {
    position: absolute;
    top: 10px;
    right: 16px;
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
}

</style>
