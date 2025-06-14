<!--<style>
#record_component {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center; /* Center items horizontally */
  justify-content: flex-start; /* Start from the top to keep button in place */
  padding-top: 20px; /* Optional, for spacing */
  box-sizing: border-box;
}

/* Fix button width and alignment */
button.btn.btn-danger {
  min-width: 150px; 
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* Optional: add fixed height if needed to prevent shifting */
  height: 40px; 
  margin-bottom: 10px; /* space below button for consistent layout */
}

/* Container for the video */
#recordingVideo {
  margin-top: 10px; 
  width: 100%; 
  display: flex;
  justify-content: center;
  /* Optional: set a max width for your video if needed */
}

/* Optional: prevent container from collapsing when video is not visible */
#video-wrapper {
  height: auto; /* or fixed height if needed */
  display: flex;
  align-items: center;
  justify-content: center;
}
/*#record_component {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center; 
  justify-content: center;
button.btn.btn-danger {
  min-width: 150px; 
  display: inline-flex; 
  align-items: center; 
  justify-content: center; 
#recordingVideo {
  margin-top: 10px; 
  width: 100%; 
  display: flex;
  justify-content: center;
}
}*/

</style>-->
<template>
    <!-- Tap once for start recording, Tap once for stopping -->
    <!--https://getbootstrap.com/docs/4.3/getting-started/introduction/-->
    <!--#845C5C-->
    <!--https://www.vecteezy.com/video/9863295-audio-spectrum-line-animation-with-2d-concept-and-white-background-->
    <!--https://app.lottiefiles.com/animation/5f62f69b-8280-4704-96f8-8d500a7c8323?panel=download-->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
    
<div ref="record_component" :width="clientWidth" :height="clientHeight" :align="left">
    <button
  type="button"
  class="btn btn-danger"
  @click="isRecording ? stopRecording() : startRecording()"
>
  <svg v-if="!isRecording" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-mic" viewBox="0 0 16 16">
    <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5"/>
    <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0zM8 0a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V3a3 3 0 0 0-3-3"/>
  </svg>
  <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-stop" viewBox="0 0 16 16">
    <path d="M3.5 5A1.5 1.5 0 0 1 5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11zM5 4.5a.5.5 0 0 0-.5.5v6a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5V5a.5.5 0 0 0-.5-.5z"/>
  </svg>
  {{ isRecording ? 'Stop recording' : 'Start recording' }}
</button>

</div>
<div  id="recordingVideo" :style="{ visibility: isRecording ? 'visible' : 'hidden' }">
     <div >
                <video id="recordingVideo"
                src="./media/vecteezy_audio-spectrum-line-animation-with-2d-concept-and-white_9863295_trimmed.mp4"  autoplay loop muted :width="clientWidth-Padding.right" height="250"></video> 
            </div>
</div>

    

</template>


<script setup>


import {ref,onMounted} from 'vue';

const isRecording = ref(false)
const clientWidth = ref(800);
const clientHeight = ref(800);
const Padding = {
top: 20,
right: 20,
bottom: 20,
left: 20,
};
const record_component = ref(null)

function startRecording() {
    isRecording.value = true;
    console.log("Recording started")
    
}
function stopRecording() {   
    isRecording.value = false;
    console.log("Recording stoppen")
}

  onMounted(() => {
      if (record_component.value) {
      clientWidth.value = record_component.value.clientWidth;
    }
    });
</script>