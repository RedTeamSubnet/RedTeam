---
title: 1. Preparation
tags: [preparation]
---

# 1. Preparation

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

## 1. Set up your workspace environment

1.1. Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects/redteam61

# Enter into projects directory:
cd ~/workspaces/projects/redteam61
```

1.2. Create conda environment with python 3.10 and pip:

```sh
conda create -y -n redteam python=3.10 pip

# Activate conda environment:
conda activate redteam
```

## 2. Setup Your Bittensor Wallet

- [**Bittensor Wallet**](../../manuals/bittensor/wallet/README.md)
    - [**2.1. Create Your Wallet**](../../manuals/bittensor/wallet/create.md)
    - [**2.2. Fund Your Wallet**](../../manuals/bittensor/wallet/fund.md)
    - [**2.3. Register Your Wallet on Subnet**](../../manuals/bittensor/register.md)
