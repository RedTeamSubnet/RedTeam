---
title: 1. Preparation
tags: [preparation]
---

# 1. Preparation

## Check system requirements

!!! warning "System Requirements"
    Below is the minimum system requirements for running a miner node:

    - 2 cores CPU
    - 8GB RAM
    - 50GB storage
    - Stable internet connection
    - Linux-based OS (Ubuntu >= 22.04 LTS)

## Install prerequisites

- Install **curl**
- Install [**git**](https://git-scm.com/install)
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../../manuals/installation/miniconda.md)**
- Install [**docker** and **docker compose**](../../manuals/installation/docker.md)

## Set up your workspace environment

Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects/redteam61

# Enter into projects directory:
cd ~/workspaces/projects/redteam61
```

Create conda environment with python 3.10 and pip:

```sh
conda create -y -n redteam python=3.10 pip

# Activate conda environment:
conda activate redteam
```
