---
title: Validator
tags:
    - validator
---

# 🛡️ Getting Started - Validator

## Step 1: Prerequisites

???+ warning inline end "System Requirements"
    - **Server**: Bare metal
    - **CPU**: 8+ cores
    - **RAM**: 32GB+
    - **Storage**: 512GB+
    - **OS**: Ubuntu 22.04 LTS+ recommended
    - **Network**: Stable high-speed internet connection

- Install [**git**](https://git-scm.com/install) to clone repositories.
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../manuals/installation/miniconda.md)**
- Install [**docker** and **docker compose**](../manuals/installation/docker.md)
- Setup your [**Bittensor wallet**](../manuals/bittensor/wallet/README.md)
- Stake sufficient TOA tokens to run a validator node on RedTeam Subnet.

## Step 2: Clone the validator repository

Create a dedicated directory for RedTeam Subnet projects (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects/redteam61

# Enter into projects directory:
cd ~/workspaces/projects/redteam61
```

Clone the validator repository:

```bash
git clone https://github.com/RedTeamSubnet/validator.git && \
    cd validator
```

## Step 3: Run validator node

### 3.1. Configure environment variables

!!! danger "IMPORTANT"
    Make sure to change the **wallet directory**, **wallet name**, and **hotkey name** variables in the **`.env`** file to match your wallet and hotkey:

    ```sh
    RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets" # !!! CHANGE THIS TO REAL WALLET DIRECTORY !!!
    RT_MINER_WALLET_NAME="miner" # !!! CHANGE THIS TO REAL MINER WALLET NAME !!!
    RT_MINER_HOTKEY_NAME="default" # !!! CHANGE THIS TO REAL MINER HOTKEY NAME !!!
    ```

```sh
# Copy '.env.example' file to '.env' file:
cp -v ./.env.example ./.env

# Edit environment variables to fit in your environment
nano ./.env
```

### 3.2. Validate docker compose configuration

```sh
# Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config
```

### 3.3. Start validator node as docker container

```sh
# Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f --tail 100
```

## Step 4: Monitor your validator

Once running, monitor your validator's logs:

```sh
# Check validator logs:
./compose.sh logs agent-validator
# Or:
docker compose logs -f --tail 100 agent-validator
```

!!! warning "IMPORTANT"
    Check your validator's performance and VTRUST score on the network.
