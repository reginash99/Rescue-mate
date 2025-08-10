<template>
  <div class="transcription-main" :class="{ 'is-busy': status }">
    <h1>Transcription</h1>
    <div class="transcription">
      <div v-if="data">
        <!-- Displaying the transcription text if not empty -->
        <p v-if="data['text'] && data['text'].trim() !== ''">{{ data["text"] }}</p>
        <!-- Displaying the following string otherwise -->
        <p v-else>No transcription available.</p>
      </div>
      <!-- Busy overlay -->
        <div v-if="status" class="overlay">
          <div class="spinner"></div>
          <div class="overlay-text">Processing…</div>
        </div>
    </div>
  </div>
</template>

<script setup>

defineProps({
  data: Object,
  status: { type: Boolean, default: false },
})
</script>

<style scoped>

.transcription-main {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.transcription {
  flex: 1 1 0;
  display: flex;
  padding: 10px;
  font-size: large;
  background-color: #EEEEEE;
  box-sizing: border-box;
  margin: 15px;
  overflow-y: auto;
  overflow-x: auto;
}

h1 {
  text-align: left;
  margin: 1% 0 0 2%;
  box-sizing: border-box;
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

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

