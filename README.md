# Rescue-mate

Naming Convention:
f = frontend
b = backend
f_component_something
b_component_something


# Installation
# SE Mamba
For SE Mamba, a Linux-based system is required, but since we are operating on Windows, we will use WSL on windows and install Ubuntu using it (there are tutorials on how to make this work but it is fairly simple and involves only terminal commands). By doing this, we will be able to use the Ubuntu terminal on our respective windows devices.

WSL, conda is required, Pytorch, Torchaudio, and Cuda are required. 

First it is recommended to install miniconda on Ubuntu and create a conda virtual environment with the specified pytorch, torchaudio versions, we used python 3.11, as well as a cuda-toolkit 12.1 and activate it. 

Then install using conda all the packages in requirements.txt. Be careful to use pysoundfile instead of soundfile and skip argparse, torch and torchaudio. You might also need to install triton 2.3.0 using pip instead of conda.

Then we need to build the mamba_ssm by running (inside the backend folder): 
    cd mamba_install
    pip install .

# Whisper
We install whisper using: pip install openai-whisper. Then import whisper inside mamba and after mamba is done cleaning up the background noise and before it is saved, we call whisper to transcribe it and save the transcription as a json file. 

