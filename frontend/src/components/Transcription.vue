<template>
  <div class="transcription-main" :class="{ 'is-busy': status }">
    <h1>Transcription</h1>
    <div class="transcription">
      <div v-if="data">
        <!-- Displaying the transcription text if not empty -->
        <p v-if="data['transcription'] && data['status']">{{ data["transcription"] }}</p>
        <!-- Displaying the following string otherwise -->
        <p v-else>No transcription available.</p>
      </div>
      <!-- Busy overlay -->
        <div v-if="status" class="overlay">
          <div class="spinner"></div>
          <div class="overlay-text">Processing…</div>
        </div>
      </div>
      <div class="side-panel-overlay" v-if="panelOpen">
        <div class="side-panel-content">
          <p>Updated transcription..
          </p>
        </div>
      </div>
    </div>
    <button class="btn floating-btn" @click="panelOpen = !panelOpen">
      <i>AI</i>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  data: Object,
  status: { type: Boolean, default: false },
})

const panelOpen = ref(false)
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
  overflow-y: auto;
  align-items: stretch;
}

.transcription.shrunk {
  flex: 0 1 50%;
  max-width: 50%;
}

.transcription-text {
  transition: width 0.3s, max-width 0.3s;
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
  bottom: 24px;
  right: 24px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: rgb(0, 192, 6);
  color: white;
  border: none;
  box-shadow: 0 4px 16px rgb(0, 0, 0);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  cursor: pointer;
  z-index: 10;
  transition: background 0.2s, box-shadow 0.2s;
}

.floating-btn:hover {
  background-color: rgb(255, 255, 255);
  box-shadow: 0 8px 32px rgba(0,0,0,0.22);
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

/* Side Panel */
.side-panel-overlay {
  top: 0;
  right: 0;
  width: 50%;
  height: 100%;
  position: absolute;
  border-radius: 0 15px 15px 0;
  background-color: var(--color-background);
  overflow: visible;
  padding: 15px;
  display: flex;
  transition: opacity 0.3s;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
