---
title: 1. Prepare Environment
tags: [preparation]
---

# 1. Prepare Environment

## System requirements

!!! warning "System Requirements"
    Below is the minimum system requirements for running a miner node:

    - **CPU**: 2+ cores
    - **RAM**: 8GB+
    - **Storage**: 50GB+
    - **OS**: Linux-based (Ubuntu 22.04 LTS+ recommended)
    - **Network**: Stable internet connection

## Prerequisites

- Install and open **Terminal** or **Command Line Interface** to run commands.
- Install **curl**
- Install [**git**](https://git-scm.com/install)
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../../manuals/installation/miniconda.md)**
- Install [**docker** and **docker compose**](../../manuals/installation/docker.md)

## Set up your workspace environment

### 1. Prepare projects directory (if not exists)

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects/redteam61

# Enter into projects directory:
cd ~/workspaces/projects/redteam61
```

### 2. Create conda environment with python 3.10 and pip

```sh
conda create -y -n redteam python=3.10 pip

# Activate conda environment:
conda activate redteam
```

## Next step

- [**2. Setup Bittensor Wallet**](./setup-wallet.md) for Miner node.
