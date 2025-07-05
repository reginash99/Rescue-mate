
<template>
  <div class="transcription-main">
    <h1>Transcription</h1>
    <div class="transcription">
      <div v-if="data">
        <p> {{ data["text"] }}</p>
      </div>
  <p v-else>No data received yet.</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  data: Object
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
}

h1 {
  text-align: left;
  margin: 1% 0 0 2%;
  box-sizing: border-box;
}
</style>

