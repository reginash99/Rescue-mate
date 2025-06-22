<template>
  <div class="grid-container">
    <div class="grid-item" style="grid-column: 1; grid-row: 1;">
      <h1>Map</h1>
    </div>
    <div class="grid-item" style="grid-column: 1; grid-row: 2;">
      <h1>History</h1>
    </div>
<div class="grid-item">
  <h1>Recording</h1>
  <button @click="startRecording" :disabled="recording">Start Recording</button>
  <button @click="stopRecording" :disabled="!recording">Stop Recording</button>
  <button @click="uploadRecording" :disabled="!recordedBlob">Upload & Transcribe</button>
  <div v-if="loading">⏳ Uploading...</div>
  <div v-if="result">{{ result }}</div>
</div>
    <div class="grid-item">
      <Transcription/>
    </div>
  </div>
</template>

<script setup>
import Transcription from "../src/components/Transcription.vue";

</script>

<script>
export default {
  data() {
    return {
      recording: false,
      recordedBlob: null,
      mediaRecorder: null,
      chunks: [],
      loading: false,
      result: ""
    };
  },
  methods: {
    async startRecording() {
      this.chunks = [];
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(stream);
        this.mediaRecorder.ondataavailable = e => this.chunks.push(e.data);
        this.mediaRecorder.onstop = this.handleStop;
        this.mediaRecorder.start();
        this.recording = true;
      } catch (err) {
        console.error("Failed to start recording:", err);
      }
    },
    stopRecording() {
      if (this.mediaRecorder) {
        this.mediaRecorder.stop();
        this.recording = false;
      }
    },
    handleStop() {
      this.recordedBlob = new Blob(this.chunks, { type: "audio/webm" });
    },
    async uploadRecording() {
      if (!this.recordedBlob) return;
      this.loading = true;

      const formData = new FormData();
      formData.append("file", this.recordedBlob, "recording.webm");

      try {
        const response = await fetch("http://localhost:8000/transcribe", {
          method: "POST",
          body: formData
        });
        const data = await response.json();
        this.result = data.text;
      } catch (error) {
        console.error(error);
        this.result = "❌ Failed to transcribe.";
      } finally {
        this.loading = false;
      }
    }
  }
};

</script>

<style>
#app {
  font-family: "Roboto Mono";
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: 1fr 1fr;
  gap: 5px;
  height: calc(100vh - 20px);
  width: calc(100vw - 20px);
  box-sizing: border-box;
  border-width: .5px;
  border-style: solid;
  border-color: black;
  padding: 0;
  margin: 0;
}

.grid-item {
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  border-width: .5px;
  border-style: solid;
  border-color: black;
}

@media (max-width: 900px) {
  .grid-container {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 1fr);
    height: 100vh;
    width: auto;
  }
}
</style>
