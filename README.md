# Rescue-mate

Naming Convention:
- f = frontend
- b = backend
- f_component_something
- b_component_something


# Installation
# SE Mamba
For SE Mamba (the code is inside the backend folder), a Linux-based system is required, but since we are operating on Windows, we will use WSL on windows and install Ubuntu using it (there are tutorials on how to make this work but it is fairly simple and involves only terminal commands). By doing this, we will be able to use the Ubuntu terminal on our respective windows devices.

WSL, conda is required, Pytorch, Torchaudio, and Cuda are required. 

First it is recommended to install miniconda on Ubuntu. Then create a conda virtual environment with python version 3.11 and activate it. After that use conda to install pytorch, torchaudio versions 2.2.2 as said in the requirements.txt inside the backend folder, torchvision, as well as cuda-toolkit (or pytorch-cuda, or both) version 12.1.

Then install all the packages in requirements.txt (again, the one inside the backend folder). Use pysoundfile instead of soundfile and skip argparse, torch, and torchaudio. You might need to uninstall triton then reinstall it again, version 2.2.0 using pip instead of conda. You might also need to downgrade numpy to 1.26. 

Then we need to build the mamba_ssm by running (inside the backend folder): 
1.  cd mamba_install
2.    pip install .

# Whisper
We install whisper using the command: pip install openai-whisper (still inside the same conda environment). 
Then we import whisper inside mamba (interface.py) and after mamba is done cleaning up the background noise but before it is saved we call whisper to transcribe it and save the transcription as a json file. 

