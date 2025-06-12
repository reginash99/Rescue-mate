# Rescue-mate

Naming Convention:
f = frontend
b = backend
f_component_something
b_component_something


# Installation
# SE Mamba
For SE Mamba, a Linux-based system is required, but since we are operating on Windows we will use WSL on windows. 

WSL is required. 
Conda is required. 
Pytorch, Torchaudio and Cuda are required. 

After installation of conda on Ubuntu, create a conda environment with the specified pytorch and torchaudio versions as well as a cuda-toolkit and activate it. 

Then, when installing the requirements.txt packages, run conda install pysoundfile instead of soundfile and skip argparse, torch and torchaudio. 

Then run: 
    cd mamba_install
    pip install .

# Whisper

