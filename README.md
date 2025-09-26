# Rescue-mate

Naming Convention:
- f = frontend
- b = backend
- f_component_something
- b_component_something

## BACKEND
# SE Mamba
For SE Mamba (the code is inside the backend folder), a Linux-based system is required, but since we are operating on Windows, we will use WSL on windows and install Ubuntu 22.04 using it (there are tutorials on how to make this work but it is fairly simple and involves only terminal commands). By doing this, we will be able to use the Ubuntu terminal on our respective windows devices.


WSL, conda, Pytorch, Torchaudio, and Cuda are required. 


Firstly, it is recommended to install miniconda on Ubuntu. Then create a conda virtual environment with python version 3.11 and activate it. After that use these commands one by one to first install pytorch, torchaudio and cuda-toolkit:  


`conda install pytorch=2.2.2 -c conda-forge -c pytorch -c nvidia`

`conda install torchaudio=2.2.2 torchvision -c conda-forge -c pytorch -c nvidia`

`conda install cuda-toolkit=12.1 -c conda-forge -c pytorch -c nvidia`


Install all the packages stated in the requirements.txt file inside the project root folder using the same command style: conda install... (excluding openai-whisper and deepfilernet, see below), and make sure to include all the channels: -c conda-forge, -c pytorch, -c nvidia (sometimes you might need to install pytorch-cuda as well, version 12.1). 


Install openai-whisper and deepfilternet by using pip instead of conda. Install openai-whisper, sentence-transformers, deepfilternet, fastapi, uvicorn only after you finish building mamba_ssm.  


Sometimes when installing them in a single command it may cause issues. If this happens, try to install them one by one, for example: conda install python-multipart -c conda-forge -c pytorch -c nvidia, conda install packaging -c conda-forge -c pytorch -c nvidia etc.


If you get errors including the package triton, you might need to uninstall it then reinstall it again, version 2.2.0 using pip instead of conda. 
You might also need to downgrade numpy to 1.26.


Then we need to build the mamba_ssm by running (inside the backend folder): 
1.  cd mamba_install
2.    pip install .



If you run into trouble with nvcc run these in the terminal: 

`sudo rm /usr/local/cuda/bin/nvcc`


And see if you get a value, if not then you need to install nvcc or reinstall pytorch, torchaudio and torchvision. 


If you still have issues with cuda even though it is installed, these commands help the system recognize and find where it is installed: 


`export CUDA_HOME=$CONDA_PREFIX`

`export PATH="$CUDA_HOME/bin:$PATH"`

`export CPLUS_INCLUDE_PATH="$CUDA_HOME/include"`

`export C_INCLUDE_PATH="$CUDA_HOME/include"`


To backup your current environment (if you need it just in case) run: 
conda list --explicit > env-backup.txt


# Whisper
After each check and subsequent filter combo is deemed appropriate, Whisper is used to transcribe. The transcription from whisper is used by several functions to calculate a score by using both average log probability and a multilingual sentence transformer model that validates how 'correct' it is and essentially how much sense it makes context wise. This score is then used to compare this script with the next one to determine which is best. In the end, only the best one is written/saved.


Whisper is also fine tuned with parameters and a prompt in german (the prompt might still need work).
Extra functions are also implemented to ensure the repetition of words or sentences whisper does sometimes doesnt happen again.


# Filters
We added deepfilternet3 for speech enhancement and a bandpass filter for more thorough noise cleaning. After these, then whisper is called to transcribe. We are using the "small" model for whisper because it takes less time, we might use "medium" as well, this is still being tested.


With these changes we managed to make the entire pipeline run in under approximately 30 seconds for a 1 minute audio input, which is a great improvement from the initial 3 minutes that this took.


So far we have changed the way files are processed so that only the last added input audio (into the input_audio folder) is processed instead of all of them.




# FASTAPI
This is how to start the backend server (run it on wsl ubuntu, inside the backend folder): uvicorn api_server:app --reload. 


If you face issues with the pretrained.sh encoding: Look at the bottom right of your screen, next to the UTF-8 while you are in the file pretrained.sh. Being inside the file pretrained.sh is important, the encoding does not work for the entire project, it is file dependant. After you change the encoding between them (LF and CRLF) it will appear as if you have made changes to the pretrained.sh, this is fine, save and make sure you have stopped the server. If you still get errors, try changing it back to what it was before, then save then try again.


# Checks for filters 

We noticed that when a "clean" audio was recorded and passed through the filters, the output was worse than the input. This happened because when you clean an already cleaned file, the quality will drop significantly. 


To fix this issue, we implemented several functions that calculate the noise and quality of the input audio, if it reaches certain levels, then only certain filters are applied.  Before we apply any of the filters (mamba, deepfilternet, bandpass filter) we check first if it is needed, if not, we skip it. This also improves the processing speed. 


The functions we used are: 


1. Signal to Noise Ratio (SNR) to measure how strong the desired signal (speech) is compared to background noise, higher SNR means clearer speech; 
2. Voice Activity Detector (VAD) to separate speech and non-speech segments and calculate SNR using only the speech frames as signal and the non-speech frames as noise;
3. Spectral Flatness to measure how noise-like or tone-like a signal is;
4. Background RMS (root mean square) which measures the average energy (loudness) of the background (non-speech) portions of audio to detect if the background is quiet or noisy.


# DATABASE

We use posgresql 17.6 for our database system.

Since we use WSL, install the database within your WSL system with the following command: 

```
sudo apt install postgresql
```

Start postgresql in wsl:
``` 
sudo service postgresql start
```

connect to psql:
```
sudo -u postgres psql
```

Set a password for the user postgres within psql
```
 ALTER USER postgres WITH PASSWORD 'PASSWORD_PLACEHOLDER';
```
Got to the following path within your wsl:
```
sudo nano /etc/postgresql/$(ls /etc/postgresql)/main/pg_hba.conf
```
And change the following to enable the connection via password authentification:
from  

local   all    postgres   peer 

to 

local   all    postgres   md5

Afterwards, restart posgresql:
```
sudo service postgresql restart
```

Additionally, the python library psycopg has to be installed:
In the following installation instruction examples, the database is called rescue_mate and it is listening on port 5432 but the values can be adjusted.

```
conda install psycopg 
```
the database can be installed within a terminal 

```
createdb -U postgres -p 5432 rescue_mate
```

there is one table called transcription which can be installed within a terminal
(the schema lies in migration folder of the project, the respective command has to be executed in the backend folder, otherwise adjust the path to the sql file):


```
psql -U postgres -p 5432 -d rescue_mate -f migrations/schema.sql 
```

for the connection to the database, create an .env file called .env in the backend folder with the following structure:

DB_NAME="DB_NAME_PLACEHOLDER" 

DB_USER="USER_PLACEHOLDER" 

DB_PASSWORD="PASSWORD_PLACEHOLDER" 

DB_HOST="HOST_PLACEHOLDER"

DB_PORT="PORT_PLACEHOLDER"

Usually, in postgresql the default port is 5432 and the default user is postgres. 

Important is that the port is not listening to other running processes.

to read the .env file, the following package has to be installed:

```
pip install python-dotenv
```

#SERVER

For deploying the application, it is necessary to add two environment variables to the .env file with the following structure:

INPUT_AUDIO_DIR="PATH_WITHIN_SERVER_TO_STORE_AUDIO_INPUTS"

OUTPUT_AUDIO_DIR="PATH_WITHIN_SERVER_TO_STORE_AUDIO_OUTPUTS"

The audio files are deleted after 24h

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

To display the transcription received from the backend, it is put together with a timestamp in an object and emitted. The timestamp is recorded when the recording starts. Upon emission, a handleData function is triggered which sends this object to the trancription component and the history component. 

# Transcription

The text "No data received yet." is displyed by default and the text "No transcription available." is displayed in case the received transcription is empty. Otherwise, the transcription is displayed as is.


# History

To show a history of transcriptions, a table with unique IDs, a timestamp, and a status (successful - not empty transcription, fail - empty transcription) is displayed.

# USER

## Microphone permissions
Ensure that you have **allowed microphone permissions** for the website. A recording cannot be started otherwise. **Reload the page** after allowing permissions for the microphone.

## Starting a Recording
Click on the red "Start recording" button to start a recording. An audio spectrum/wave will be appear and the button's text will change to 'Stop recording' to indicate that the recording has started. A processing buffer will also appear in the trancription box during processing.

Record your audio and click the same button to stop the recording. Once the audio is recorded, it will be sent to the backend for processing. This may take a few seconds, depending on the length of the audio. 

A new audio cannot be recorded during this processing, therefore, the recording button is disable (will be greyed and cannot be clicked on). The button will be enabled again once the processing is complete.

## Transcription
Once the transcription is available, it will appear in the transcription view. In case the audio could not be transcribed, "No transcription available" text will be displayed instead.

## History
Records of each trancription along with a unique *ID*, a *timestamp* (at the time the recording is started), and a *status* are saved in the database and displayed in the History table in the frontend. A _View_ button can be seen in each row of the displayed record. Click on this _View_ button to view the trancription of the selected record.

### Status
A _Success_ status is displayed in case a transcription is available for the recorded audio. A _Failed_ status is displayed otherwise.

### Saving Records
All records of the trancriptions are **deleted after 24 hours**. The recorded audios themselves are not saved, only the trancriptions, IDs, and timestamps are saved.

## Map
In case any address(es) is **detected in the transcription** of the recording that exists in the region of Hamburg, it will be displayed in the map with a pin. Hovering on the pin will display the address detected.

## Resizing
The components can be resized to your liking by dragging the bottom right corner of the recording box that is also highlighted by two lines. The maximum and minimum widths are set according to the size of your screen.

## Themes
The theme of the webite follows the theme of your browser. There are two themes available, dark and light.


## Citation

Citing Mamba:
```
@article{mamba,
  title={Mamba: Linear-Time Sequence Modeling with Selective State Spaces},
  author={Gu, Albert and Dao, Tri},
  journal={arXiv preprint arXiv:2312.00752},
  year={2023}
}
```
