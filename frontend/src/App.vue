<template>
  <div id="app">
    <h1>🎤 Transcribe Audio</h1>

    <input type="file" @change="handleFile" accept="audio/*" />
    <button :disabled="!file" @click="uploadAudio">Transcribe</button>

    <div v-if="loading">⏳ Transcribing...</div>
    <div v-if="result">
      <h2>📝 Result</h2>
      <pre>{{ result }}</pre>
    </div>
  </div>
</template>

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
  font-family: Avenir, Helvetica, Arial, sans-serif;
  padding: 2em;
  max-width: 600px;
  margin: auto;
  text-align: center;
}
input {
  margin: 1em 0;
}
</style>
