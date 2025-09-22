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


First it is recommended to install miniconda on Ubuntu. Then create a conda virtual environment with python version 3.11 and activate it. After that use these commands one by one:  


`conda install pytorch=2.2.2 -c conda-forge -c pytorch -c nvidia`

`conda install torchaudio=2.2.2 torchvision -c conda-forge -c pytorch -c nvidia`

`conda install cuda-toolkit=12.1 -c conda-forge -c pytorch -c nvidia`

`conda install sentence-transformers`

As stated in the requirements.txt file inside the project root folder (as well as cuda-toolkit (or pytorch-cuda, or both), version 12.1)


Then, install all the packages listed in requirements.txt (located inside the project root folder). Use pysoundfile instead of soundfile and skip argparse, torch, and torchaudio. You might need to uninstall triton then reinstall it again, version 2.2.0 using pip instead of conda. You might also need to downgrade numpy to 1.26.
Use the command: 

`conda install packaging librosa pysoundfile pyyaml tensorboard pesq einops -c conda-forge -c pytorch -c nvidia`


Sometimes when installing them in a single command it may cause issues. If this happens, try to install them separately, for example: conda install python-multipart -c conda-forge -c pytorch -c nvidia, conda install packaging -c conda-forge -c pytorch -c nvidia etc.


We are also using the package webrtcvad to determine whether the audio contains speech. To install this, run the command: `conda install -c conda-forge webrtcvad`


Then we need to build the mamba_ssm by running (inside the backend folder): 
1.  cd mamba_install
2.    pip install .



If you run into trouble with nvcc run these in the terminal: 

`sudo rm /usr/local/cuda/bin/nvcc`


`export CUDA_HOME=$CONDA_PREFIX`

`export PATH="$CUDA_HOME/bin:$PATH"`

`export CPLUS_INCLUDE_PATH="$CUDA_HOME/include"`

`export C_INCLUDE_PATH="$CUDA_HOME/include"`


To backup your current environment run: 
conda list --explicit > env-backup.txt


# Whisper
Install using the command: `pip install openai-whisper`.
After each check and subsequent filter combo is deemed appropriate, Whisper is used to transcribe. The transcription from whisper is used by several functions to calculate a score by using both average log probability and a multilingual sentence transformer model that validates how 'correct' it is and essentially how much sense it makes context wise. This score is then used to compare this script with the next one to determine which is best. In the end, only the best one is written/saved.

Whisper is also fine tuned with parameters and a prompt in german (the prompt might still need work).
Extra functions are also implemented to ensure the repetition of words or sentences whisper does sometimes doesnt happen again.


We tried faster-whisper as well, but the resulting transcription was not that much different from the one we get with whisper so we decided not to use it. 


# Filters
We added deepfilternet3 for speech enhancement and a bandpass filter for more thorough noise cleaning. To install this you need to run the command: `pip install deepfilternet`. After these, then whisper is called to transcribe. We are using the "small" model for whisper because it takes less time, we might use "medium" as well, this is still being tested.


We  changed mamba's model parameter hop_size (they are samples between successive frames) from 100 to 200. 

With these changes we managed to make the entire pipeline run in under approximately 30 seconds for a 1 minute audio input, which is a great improvement from the initial 3 minutes that this took.


So far we have changed the way files are processed so that only the last added input audio (into the input_audio folder) is processed instead of all of them.




# FASTAPI
In order for the api to work, you need to run these commands (all of these inside your conda environment): 


`conda install fastapi -c conda-forge -c pytorch -c nvidia`
`conda install uvicorn -c conda-forge -c pytorch -c nvidia`
`conda install python-multipart c conda-forge -c pytorch -c nvidia`


This is how to start the backend server (run it on wsl ubuntu, inside the backend folder): uvicorn api_server:app --reload. 


Keep in mind that pretrained.sh needs to be encoded in CRLF. Look at the bottom right of your screen, next to the UTF-8 while you are in the file pretrained.sh. Being inside the file pretrained.sh is important, the encoding does not work for the entire project, it is file dependant. After you change the encoding to CRLF it will appear as if you have made changes to the pretrained.sh, this is fine. If you still get errors, try changing it back to LF, then save then try again. Change between them (LF and CRLF) and save when you face errors. 


# Checks for filters 

We noticed that when a "clean" audio was recorded and passed through the filters, the output was worse than the input. This happened because when you clean an already cleaned file, the quality will drop significantly. 
To fix this issue, we implemented several functions that calculate the noise and quality of the input audio, if it reaches certain levels, then only certain filters are applied.  Before we apply any of the filters (mamba, deepfilternet, bandpass filter) we check first if it is needed, if not, we skip it. This also improves the processing speed. 


The functions we used are: 


1. Signal to Noise Ratio (SNR) to measure how strong the desired signal (speech) is compared to background noise, higher SNR means clearer speech; 
2. Voice Activity Detector (VAD) to separate speech and non-speech segments and calculate SNR using only the speech frames as signal and the non-speech frames as noise;
3. Spectral Flatness to measure how noise-like or tone-like a signal is;
4. Background RMS (root mean square) which measures the average energy (loudness) of the background (non-speech) portions of audio to detect if the background is quiet or noisy.


# DATABASE

We use posgresql 17.6 for our database system, which means you have to [install](https://www.postgresql.org/download/) it.

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
from  <br>
local   all    postgres   peer <br>
to <br>
local   all    postgres   md5

Afterwards, restart posgresql:
```
sudo service postgresql restart
```

Additionally, the python library psycopg has to be installed:
In the following installation instruction examples, the database is called rescue_mate and it is listening on port 5432 but the values can be adjusted.

```
npm install psycopg2
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

for the connection to the database, an .env file in the backend folder is required with the following structure:

DB_NAME="DB_NAME_PLACEHOLDER" <br>
USER="USER_PLACEHOLDER" <br>
PASSWORD="PASSWORD_PLACEHOLDER" <br>
HOST="HOST_PLACEHOLDER"<br>
PORT="PORT_PLACEHOLDER"

Usually, in postgresql the default port is 5432 and the default user is postgres. <br>
Important is that the port is not listening to other running processes.

to read the .env file, the following package has to be installed:

```
pip install python-dotenv
```

we have three transcations that interact with the DB
insert_record(timestamp, transcription)
delete_records() (all records are deleted that are older than 24h)
select_records() 

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
