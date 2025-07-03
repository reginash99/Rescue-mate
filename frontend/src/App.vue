<template>
  <div class="grid-container">
    <div class="grid-item">
      <Map/>
    </div>
    <div class="grid-item">
      <Record/>
    </div>
    <div class="grid-item">
      <HistoryTable/>
    </div>
    <div class="grid-item">
      <Transcription/>
    </div>
  </div>
  
   
</template>

<script setup>
import Transcription from "../src/components/Transcription.vue";
import HistoryTable from "./components/HistoryTable.vue";
import Map from "./components/Map.vue";
import Record from "./components/Record.vue";
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
  align-items: stretch;
  justify-content: stretch;
  border-width: .5px;
  border-style: solid;
  border-color: black;
  height: 100%;
  min-height: 0;
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
