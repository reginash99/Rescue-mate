
<template>
  <div class="grid-container">
    <div class="grid-item record">
      <Record @transcription="handleData" @waitingForRecording="indicateRecordingStatus" />
    </div>

    <div class="grid-item transcript">
      <!-- Listen for markers-found from Transcription -->
      <Transcription
        :data="transcriptionData"
        :status="waitingForRecording"
        @markers-found="onMarkersFound"
        @final-transcription="updateHistoryTable"
      />
    </div>

    <div class="grid-item history">
      <HistoryTable 
      :history="history" 
      />
    </div>

    <div class="grid-item map">
      <!-- Pass markers down to Map -->
      <Map :markers="markers" />
    </div>
  </div>
</template>

<script setup>
import { ref,onMounted } from 'vue';
import Transcription from "../src/components/Transcription.vue";
import HistoryTable from "./components/HistoryTable.vue";
import Map from "./components/Map.vue";
import Record from "./components/Record.vue";

const transcriptionData = ref(null);
const history = ref([]);
const waitingForRecording = ref(false);

// NEW: markers state
const markers = ref([]);

// update history table when final transcription is ready
function updateHistoryTable(update) {
  if (update){
    addHistoryEntry();
  }
  

}
// NEW: handler receives markers from Transcription
function onMarkersFound(m) {
  markers.value = Array.isArray(m) ? m : [];
}

function indicateRecordingStatus(status) {
  waitingForRecording.value = !!status;
}

function handleData(data) {
  // This function is called when the Record component emits data
  // It sends the transcription to the Transcription component
  // and pushes it to the HistoryTable component as a new entry
  sendTranscription(data)
  addHistoryEntry()
}

function sendTranscription(data) {
  transcriptionData.value = data;
}

async function addHistoryEntry() {
  await get_records()
}

onMounted(async() =>
{
    await get_records()
}
)

async function get_records() {
    try {
    const response = await fetch('/get-history')
    if (!response.ok) {
      throw new Error('Network response was not ok')
    }
    const result = await response.json()
   
    history.value = result.history

  } catch (error) {
    console.error('Fetch error:', error)
  }
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
  grid-template-columns: 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  height: calc(100vh - 20px);
  width: calc(100vw - 20px);
  box-sizing: border-box;
  padding: 10;
}

.grid-item {
  background: var(--grid-item-backgound-color);
  display: grid;
  justify-content: stretch;
  border-width: .5px;
  border-style: solid;
  height: 100%;
  min-height: 0;
  border-radius: 25px;
  box-shadow: 0 7px 10px var(--shadow-color);
  border-color: var(--grid-item-border);
  overflow: hidden;
}

.record {
  resize: horizontal;
  min-width: calc(100vw - 65vw);
  max-width: calc(100vw - 35vw);
}
.transcript, .map {
  min-width: calc(100vw - 70vw);
  max-width: calc(100vw - 30vw);
}

.transcript {
  resize: vertical !important;
}

@media (max-width: 900px) {
  .grid-container {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 1fr);
    height: 100vh;
    width: auto;
  }

  .grid-item {
    max-width: 100%;
    min-width: 100%;
    height: calc(100vh / 2 - 10px);
    border-radius: 0;
    resize: none;
  }
}

/* Scrollbar customization */
::-webkit-scrollbar {
  width: 7px;
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--scrollbar-color);
  border-radius: 12px;
  border: 2px solid var(--grid-item-backgound-color);
}

::-webkit-scrollbar-track {
  background: transparent;
}
</style>
