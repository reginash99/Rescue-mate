<template>
  <!-- Tap once for start recording, Tap once for stopping -->
  <!--https://getbootstrap.com/docs/4.3/getting-started/introduction/-->
  <!--#845C5C-->
  <!--https://www.vecteezy.com/video/9863295-audio-spectrum-line-animation-with-2d-concept-and-white-background-->

  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css"
    integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">

  <div :style="{ width: '100%', height: '100%' }">
    <div ref="record_component"
      :style="{ width: '100%', height: '50%', position: 'relative', display: 'flex', alignItems: 'last baseline', justifyContent: 'center' }">

      <button type="button" :class="{'btn btn-danger': !waitingForRecording, 'btn btn-secondary': waitingForRecording}" @click="isRecording ? stopRecording() : startRecording()" :disabled="waitingForRecording">
        <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }">
          <svg v-if="!isRecording && !waitingForRecording" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
            class="bi bi-mic" viewBox="0 0 16 16">
            <path
              d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5" />
            <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0zM8 0a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V3a3 3 0 0 0-3-3" />
          </svg>

          <svg v-else-if="isRecording && !waitingForRecording" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-stop"
            viewBox="0 0 16 16">
            <path
              d="M3.5 5A1.5 1.5 0 0 1 5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11zM5 4.5a.5.5 0 0 0-.5.5v6a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5V5a.5.5 0 0 0-.5-.5z" />
          </svg>
          <svg v-else width="16" height="16">  
          </svg>          
          
          <div v-if="isRecording">
            Stop recording
          </div>
          <div v-else-if="!isRecording && waitingForRecording"> 
            Recording... 
          </div>
          <div v-else>
            Start recording
          </div>
        </div>
      </button>

    </div>
    <div id="recordingVideo" :style="{ visibility: isRecording ? 'visible' : 'hidden', width: '100%', height: '50%' }">

      <div :style="{ width: '100%', height: '100%', display:'flex', alignItems:'baseline',justifyContent:'center' }">

        <video id="recordingVideo"
          src="./media/record_video_cropped.mp4" autoplay
          loop muted :style="{maxWidth: '100%', height:'100%', objectFit:'fill'}"></video>
        

      </div>

      
    </div>
    <!--this part is used for checking if the recording was generated successfully-->
    <!--<div>
  <audio controls :src="audio_url" v-if = "audio_generated"></audio>
</div>-->
  </div>


</template>


<script setup>


import { ref, onMounted } from 'vue';
import { defineEmits } from 'vue'

const emit = defineEmits(['transcription'])
const isRecording = ref(false)
const waitingForRecording = ref(false);
const clientWidth = ref(800);
const clientHeight = ref(800);
const Padding = {
  top: 20,
  right: 20,
  bottom: 20,
  left: 20,
};

const timestamp_format = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit'
}

let record_component = ref(null)
let recorder = null;
let audio = [];
let audio_url = ref(null);
let audio_generated = ref(false)
let data = []
let rec_timestamp = ref(null);

function startRecording() {
  isRecording.value = true;
  console.log("Recording started")

  audio = [];
  data = []; // Clear previous data
  recorder.start();

  if (recorder.state == "recording") {
    rec_timestamp = new Date().toLocaleString('de-DE', timestamp_format)
  }
}

function stopRecording() {
  recorder.stop();
  if (recorder.state == "inactive") {

  }
  isRecording.value = false;
  console.log("Recording stopped")
}

async function sendAudioToBackend(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/transcribe-audio/', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw new Error('Failed to get transcription');
  }
  const data = await response.json();
  // data.transcription contains the transcription JSON as a string
  return data.transcription;
}

async function sentAudio() {
  waitingForRecording.value = true;
  console.log("Sending audio to backend")
  let audio = new Blob(data, { type: "audio/webm;codecs=opus" });
  let file = new File([audio], "recording.webm", { type: "audio/webm" });

  // To check if the audio was generated successfully
   try{
  //  audio_url = window.URL.createObjectURL(audio)
  //  audio_generated.value = true;
    const backend_response = await sendAudioToBackend(file);

    console.log("Transcription received: ", backend_response);
    const parsed_transcription = JSON.parse(backend_response)

    // Putting transcription and timestamp into an object to emit
    const transcription = {
      text: parsed_transcription['text'],
      timestamp: rec_timestamp
    }
    emit('transcription', transcription)
    waitingForRecording.value = false;
    data = []; // Clear data after sending
   }
   catch (error){
     waitingForRecording.value = false;
     console.error("Error creating audio URL: ", error);
   }
}

onMounted(() => {
  if (record_component.value) {
    clientWidth.value = record_component.value.clientWidth;
  }

  if (navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia(
      {
        audio: true
      }
    )
      .then((stream) => {

        let options = { mimeType: "audio/webm;codecs=opus" };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
          options = { mimeType: "" };
        }
        recorder = new MediaRecorder(stream, options);

        recorder.ondataavailable = (event) => {
          data.push(event.data)
        }

        recorder.onstop = () => {
          sentAudio()
        }
      })
      .catch((error) => {
        console.error("Error occured: ", error)
      })
  }

});
</script>
