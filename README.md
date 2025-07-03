# Rescue-mate

Naming Convention:
- f = frontend
- b = backend
- f_component_something
- b_component_something

## BACKEND
# Installation
# SE Mamba
For SE Mamba (the code is inside the backend folder), a Linux-based system is required, but since we are operating on Windows, we will use WSL on windows and install Ubuntu using it (there are tutorials on how to make this work but it is fairly simple and involves only terminal commands). By doing this, we will be able to use the Ubuntu terminal on our respective windows devices.


WSL, conda, Pytorch, Torchaudio, and Cuda are required. 


First it is recommended to install miniconda on Ubuntu. Then create a conda virtual environment with python version 3.11 and activate it. After that use conda to install pytorch, torchaudio versions 2.2.2 as said in the requirements.txt inside the backend folder, torchvision, as well as cuda-toolkit (or pytorch-cuda, or both) version 12.1.


Then install all the packages in requirements.txt (again, the one inside the backend folder). Use pysoundfile instead of soundfile and skip argparse, torch, and torchaudio. You might need to uninstall triton then reinstall it again, version 2.2.0 using pip instead of conda. You might also need to downgrade numpy to 1.26. 


Then we need to build the mamba_ssm by running (inside the backend folder): 
1.  cd mamba_install
2.    pip install .



If you run into trouble with nvcc run these in the terminal: 

sudo rm /usr/local/cuda/bin/nvcc

export CUDA_HOME=$CONDA_PREFIX
export PATH="$CUDA_HOME/bin:$PATH"
export CPLUS_INCLUDE_PATH="$CUDA_HOME/include"
export C_INCLUDE_PATH="$CUDA_HOME/include"


To backup your current environment run: 
conda list --explicit > env-backup.txt


# Whisper
We install whisper using the command: pip install openai-whisper (still inside the same conda environment). 
Then we import whisper inside mamba (interface.py) and after mamba is done cleaning up the background noise but before it is saved we call whisper to transcribe it and save the transcription as a json file. 


# Filters
We changed how the interface.py processes audio by making it cut the audio into 3 second chunks, thus improving the speed. We added deepfilternet3 for speech enhancement and a bandpass filter for more thorough noise cleaning. To install this you need to run the command: pip install deepfilternet. After these, then whisper is called to transcribe. We are using the "small" model for whisper because it takes less time, we might use "medium" as well, this is still being tested. The pipeline so far looks like this: 


SEMamba -> Bandpass filter -> deepfilternet3 -> Whisper


After testing chunking the audio file, the resulting transcription was of bad quality, so we decided to go back to how originally mamba processed files with a few changes. One change is to use .half() when loading mamba in order to save memory, as the model is large, it saves memory by using half-precision floats. 
We also changed mamba's model parameter hop_size (they are samples between successive frames) from 100 to 200. 


With these changes we managed to make the entire pipeline run in under approximately 30 seconds for a 1 minute audio input, which is a great improvement from the initial 3 minutes that this took.


So far we have changed the way files are processed so that only the last added input audio (into the input_audio folder) is processed instead of all of them.


We tried faster-whisper as well, but the resulting transcription was not that much different from the one we get with whisper. 




## FRONTEND
# Map

For implementing the map we used Vue Map, a provided open-source UI Framework for vue.js based on Leaflet which is an open-source JavaScript library
for mobile-friendly interactive maps.

For installing this framework, execute the following command in the terminal: 

```
npm install vue-map-ui leaflet.
```

Then, import four css files in the main.ts file which are necessary for the correct rendering of the map:

```
import 'leaflet/dist/leaflet.css';
import 'vue-map-ui/dist/normalize.css';
import 'vue-map-ui/dist/style.css';
import 'vue-map-ui/dist/theme-all.css';
```
In the Map Component, add the following structure

```
<VMap  :center=center :zoom=zoom :id="VMap" :style="{width: '100%', height: '100%'}"
      <VMapOsmTileLayer />
      <VMapZoomControl />
      <VMapMarker :latlng=location />
</VMap>
```

Since our application concentrates on Hamburg, the map is centered per default around the Rathaus. 
Currently the geo data of the Hamburg Rathaus are used to display a marker in the map, demonstrating how it might look when geodata is extracted from the audio.

If no data was found, then no map but a notification will be displayed informing that no data was found.


# Recording

To record the incomming audio, we used MediaStream Recording API. Incorporating this API, it is possible to store real-time recorded audio.
Attention: It is necessary to give permisson to use the microphone of your device. It may happen that some browsers deny this per default. 

The icons are provided by bootstrap. While recording the audio, a video is shown representing that a recording is ongoing displaying the waves of a voice wave. But it doesn't represent the actual data. The clip is used from vecteezy.com and was cropped to have a smaller aspect ratio.