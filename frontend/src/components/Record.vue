<template>
    <!-- Tap once for start recording, Tap once for stopping -->
    <!--https://getbootstrap.com/docs/4.3/getting-started/introduction/-->
    <!--#845C5C-->
    <!--https://www.vecteezy.com/video/9863295-audio-spectrum-line-animation-with-2d-concept-and-white-background-->
    <!--https://app.lottiefiles.com/animation/5f62f69b-8280-4704-96f8-8d500a7c8323?panel=download-->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
    
    <div id="Record" class="container"  ref="record_component"> <!--:width="svgWidth" :height="svgHeight"-->
                <h5>Recording Section</h5>
            <div >
                <button type="button" class="btn btn-danger" id="recordButton" @click="startRecording" v-show="!isRecording">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-mic" viewBox="0 0 16 16">
                    <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5"/>
                    <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0zM8 0a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V3a3 3 0 0 0-3-3"/>
                </svg>
                
            Press me for recording
            </button>
            </div>
            <div >
                 <button type="button" class ="btn btn-danger" id="stopRecordButton" @click="stopRecording" v-show="isRecording"> 
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-stop" viewBox="0 0 16 16">
                    <path d="M3.5 5A1.5 1.5 0 0 1 5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11zM5 4.5a.5.5 0 0 0-.5.5v6a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5V5a.5.5 0 0 0-.5-.5z"/>
                </svg>

            Stop recording
            </button>
            <div >
                <video src="./media/vecteezy_audio-spectrum-line-animation-with-2d-concept-and-white_9863295_trimmed.mp4" v-show="isRecording"  alt="Recording" autoplay loop muted></video> <!--width="500" height="250"-->
            </div>
            </div>
        </div>

</template>
<script setup>


import {ref,onMounted} from 'vue';

const isRecording = ref(false)
const svgWidth = ref(800);
const svgHeight = ref(800);
const svgPadding = {
top: 20,
right: 20,
bottom: 20,
left: 20,
};
//const record_component = ref(null)

function startRecording() {
    isRecording.value = true;
    console.log("Recording started")
}
function stopRecording() {   
    isRecording.value = false;
    console.log("Recording stoppen")
}

  onMounted(() => {
      /*if (record_component.value) {
      svgWidth.value = record_component.value.clientWidth;
    }*/
    });
</script>