<template>
  <div class="transcription-main" :class="{ 'is-busy': status }">
    <h1>Transcription</h1>
    <div class="transcription" style="position:relative;">
      <div :class="['transcription-text', { shrunk: panelOpen }]">
        <div v-if="data">
          <p v-if="data['text'] && data['text'].trim() !== ''">{{ data["text"] }}</p>
          <p v-else>No transcription available.</p>
        </div>
        <div v-else>
          <p>Transcription will appear here...
            Lorem ipsum, dolor sit amet consectetur adipisicing elit. Praesentium, minus. Nostrum corporis neque commodi, maiores aliquam culpa. Quasi mollitia libero suscipit, quam a enim tenetur dolor eum excepturi laboriosam debitis.
          </p>
        </div>
        <div v-if="status" class="overlay">
          <div class="spinner"></div>
          <div class="overlay-text">Processing…</div>
        </div>
        </div>
        <div class="side-panel-overlay" v-if="panelOpen">
          <p>Side panel content
            Lorem ipsum dolor sit amet consectetur adipisicing elit. Alias, totam fugiat voluptate nulla voluptatum exercitationem, molestias perspiciatis natus excepturi esse quae, consequuntur itaque a! Sequi facere rem corporis necessitatibus delectus.
          </p>
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
  overflow: hidden;
  position: relative;
}

.transcription-main h1 {
  text-align: center;
  margin: 1% 0 0 2%;
}

.transcription-row {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100%;
  flex: 1 1 auto;
}

.transcription {
  position: relative;
  flex: 1 1 0;
  display: flex;
  padding: 15px;
  font-size: x-large;
  background-color: #EEEEEE;
  margin: 15px;
  overflow-y: auto;
  overflow-x: auto;
  border-radius: 15px;
  box-shadow: 0 5px 5px rgba(0, 0, 0, 0.144);
}

.transcription.shrunk {
  flex: 0 1 50%;
  max-width: 50%;
}

/* Dim the content when busy */
.is-busy {
  filter: grayscale(1);
  opacity: 0.5;
  pointer-events: none; /* block interactions */
}

/* Full-cover overlay */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  backdrop-filter: blur(2px);
}

/* Simple CSS spinner */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0,0,0,0.2);
  border-top-color: rgba(0,0,0,0.6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 8px;
}

.overlay-text {
  font-size: 0.9rem;
}

.side-panel-overlay {
  position: absolute;
  top: 0;
  right: 0;
  width: 50%;
  height: 100%;
  background: #000000;
  color: #EEEEEE;
  border-radius: 0 15px 15px 0;
  padding: 15px;
  display: flex;
  z-index: 2;
  transition: opacity 0.3s;
}

.transcription-text {
  transition: width 0.3s, max-width 0.3s;
  width: 100%;
  max-width: 100%;
  z-index: 1;
}

.transcription-text.shrunk {
  width: 50%;
  max-width: 50%;
}

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

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

