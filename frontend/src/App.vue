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
      file: null,
      result: "",
      loading: false
    };
  },
  methods: {
    handleFile(e) {
      this.file = e.target.files[0];
    },
    async uploadAudio() {
      if (!this.file) return;

      this.loading = true;
      const formData = new FormData();
      formData.append("file", this.file);

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
  background-color: black;
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
    height: auto;
    width: auto;
  }
  .grid-item.col2-row1,
  .grid-item.col2-row2 {
    height: auto;
    align-self: stretch;
  }
}
</style>
