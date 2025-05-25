<script setup lang="ts">
defineProps<{
  msg: string
}>()
</script>

<template>
  <div class="transcription-main">
    <h1>Transcription</h1>
    <div class="transcription">
        <p>Transcribing...</p>
    </div>
  </div>
</template>

<style scoped>
.transcription-main {
  display:grid;
  height: 100px;
}

.transcribe h1,
.transcribe h3 {
  text-align: left;
}

.transcription{
  background-color: rgb(163, 163, 163);
}

@media (min-width: 1024px) {
  .transcribe h1,
  .transcribe h3 {
    text-align: left;
  }
}
</style>
