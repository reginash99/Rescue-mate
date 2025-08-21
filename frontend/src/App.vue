<template>
  <div class="grid-container">
    <div class="grid-item">
      <Record @transcription="handleData" @waitingForRecording ="indicateRecordingStatus"/>
    </div>
    <div class="grid-item">
      <Map/>
    </div>
    <div class="grid-item">
      <HistoryTable :history="history"/>
    </div>
    <div class="grid-item">
      <Transcription :data="transcriptionData" :status="waitingForRecording"/>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import Transcription from "../src/components/Transcription.vue";
import HistoryTable from "./components/HistoryTable.vue";
import Map from "./components/Map.vue";
import Record from "./components/Record.vue";

const transcriptionData = ref(null);
const history = ref([])
const waitingForRecording = ref(false);

function indicateRecordingStatus(status) {
  // This function can be used to indicate the recording status
  // In this case, if the recording is processing or done processing
  waitingForRecording.value = !!status;
}

function handleData(data) {
  // This function is called when the Record component emits data
  // It sends the transcription to the Transcription component
  // and pushes it to the HistoryTable component as a new entry
  sendTranscription(data)
  addHistoryEntry(data)
}

function sendTranscription(data) {
  transcriptionData.value = data
}

function addHistoryEntry(data) {
  history.value.push(data)
}
</script>

<style>
#app {
  font-family: "Figtree";
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
}

.grid-container {
  display: grid;
  grid-template-columns: 1.2fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  height: calc(100vh - 20px);
  width: calc(100vw - 20px);
  box-sizing: border-box;
  padding: 10;
}

.grid-item {
  background: #ffffff;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  border-width: .5px;
  border-style: solid;
  height: 100%;
  min-height: 0;
  border-radius: 25px;
  box-shadow: 0 7px 10px rgba(0, 0, 0, 0.356);
  overflow: hidden;
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
