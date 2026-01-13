---
title: "Miniconda - Python"
tags: [conda, miniconda, python, pip, linux, macos, installation]
---

# :simple-anaconda: Install Miniconda (Conda) and Python

**Miniconda** is a runtime environment management tool that allows you to install and manage multiple isolated environments with different versions of Python and other packages.

## Official Pages

- Miniconda: <https://www.anaconda.com/docs/getting-started/miniconda/install>
- Quickstart install: <https://www.anaconda.com/docs/getting-started/miniconda/install#quickstart-install-instructions>
    - Linux: <https://www.anaconda.com/docs/getting-started/miniconda/install#linux-2>
    - macOS: <https://www.anaconda.com/docs/getting-started/miniconda/install#macos-2>

---

## Install on **Linux** or **macOS**

### 1. Download and install **Miniconda (v3)**

#### 1.1 Prepare the runtime directory for Miniconda

```sh
mkdir -pv ~/workspaces/runtimes/miniconda3
```

#### 1.2 Download Miniconda installer script

```sh
# Linux:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-$(uname -m).sh -O miniconda.sh
# macOS:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-$(uname -m).sh -O miniconda.sh
```

#### 1.3 Install Miniconda

```sh
## Install Miniconda with the following options:
# -b: run installer in batch mode (no user interaction)
# -u: update existing installation
# -p: specify the installation prefix (path)
bash miniconda.sh -b -u -p ~/workspaces/runtimes/miniconda3

# Remove downloaded script file:
rm -vrf miniconda.sh

# Activate conda environment:
source ~/workspaces/runtimes/miniconda3/bin/activate

## Set conda initialization for your shell:
# For bash:
conda init bash
# For zsh:
conda init zsh
```

#### 1.4 Post-installation steps and verification

```sh
# Accept the TOS (terms of service) for conda channels:
conda tos accept --override-channels \
    -c https://repo.anaconda.com/pkgs/main \
    -c https://repo.anaconda.com/pkgs/r

# Append 'conda-forge' community channel to the conda:
conda config --append channels conda-forge

# Disable Anaconda telemetry:
echo -e "\nplugins:\n  anaconda_telemetry: false" >> ~/.condarc


# Clean conda caches:
conda clean -av

# Update conda to the latest version:
conda update -n base conda

# Check installed conda version:
conda -V
```

### 2. Create a new conda environment

#### 2.1. Create a new conda environment with Python

```sh
# Create a new conda environment named `redteam` with `python` and `pip`:
conda create -y -n redteam python=3.10 pip

# Clean conda caches:
conda clean -av

# Activate new conda environment:
conda activate redteam

## Set default conda environment for your shell:
# For bash:
echo "conda activate redteam" >> ~/.bashrc
# For zsh:
echo "conda activate redteam" >> ~/.zshrc

# Upgrade pip to the latest version:
pip install -U pip

# Clean pip caches:
pip cache purge
```

#### 2.2. Verify Python and pip installation

```sh
# Check installed python and pip version:
python -V
pip -V
```

---

## References

- <https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html>
- <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>
- <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-channels.html>
- <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-pkgs.html>
- <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-python.html>
