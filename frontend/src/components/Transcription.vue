<script setup lang="ts">
defineProps<{
  msg: string
}>()
</script>

<template>
  <div class="trnascription-main">
    <h1 class="green">{{ msg }}</h1>
    <h3>Transcription</h3>
    <div class="transcription">
        
    </div>

  </div>
</template>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  position: relative;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

.transcribe h1,
.transcribe h3 {
  text-align: center;
}

@media (min-width: 1024px) {
  .transcribe h1,
  .transcribe h3 {
    text-align: left;
  }
}
</style>
