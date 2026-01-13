---
title: 1. Preparation
tags:
    - preparation
---

# Preparation

## Check minimum system requirements

!!! warning "System Requirements"
    Below is the minimum system requirements for running a miner node:

    - 2 core CPU
    - 8GB RAM
    - Ubuntu 22.04 LTS or later

## Install prerequisites

- Install [**git**](https://git-scm.com/install)
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](https://www.anaconda.com/docs/getting-started/miniconda/install)**
    - *[Python virtual environment]  [venv](https://docs.python.org/3/library/venv.html)*
- Install [**docker** and **docker compose**](https://docs.docker.com/engine/install)
    - Docker [**installation script**](https://github.com/docker/docker-install)
    - Docker [**post-installation steps**](https://docs.docker.com/engine/install/linux-postinstall)

## Set up your workspace environment

Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects

# Enter into projects directory:
cd ~/workspaces/projects
```

Create conda environment with python 3.10 and pip:

```sh
conda create -y -n redteam python=3.10 pip

# Activate conda environment:
conda activate redteam
```
