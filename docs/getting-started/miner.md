---
title: Miner
tags:
    - miner
---

# Getting Started - Miner

## Step 1: Prerequisites

???+ warning inline end "System Requirements"
    - **CPU**: 2+ cores
    - **RAM**: 8GB+
    - **Storage**: 50GB+
    - **OS**: Linux-based (Ubuntu 22.04 LTS+ recommended)
    - **Network**: Stable internet connection

- Install and open **Terminal** or **Command Line Interface** to run commands.
- Install **curl** to download files from the internet.
- Install [**git**](https://git-scm.com/install) to clone repositories.
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../manuals/installation/miniconda.md)**
- Install [**docker** and **docker compose**](../manuals/installation/docker.md)
- Setup your [**Bittensor wallet**](../manuals/bittensor/wallet/README.md)
    - [Create your wallet](../manuals/bittensor/wallet/create.md)
    - [Fund your wallet](../manuals/bittensor/wallet/fund.md)
    - [Register your wallet](../manuals/bittensor/wallet/register.md)
- Implement your own solution to [**solve challenges**](../challenges/README.md)
- [**Build and publish**](../miner/workflow/3.build-and-submit.md) your solution as commit

## Step 2: Clone the miner repository

Create a dedicated directory for RedTeam Subnet projects:

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects/redteam61

# Enter into projects directory:
cd ~/workspaces/projects/redteam61
```

Clone the miner repository:

```bash
git clone https://github.com/RedTeamSubnet/miner.git && \
    cd miner
```

## Step 3: Run miner node

### 3.1. Configure active commit file to submit

!!! danger "IMPORTANT"
    Make sure to change the commit hash with your own pushed docker image **SHA256 digest as commit hash** in the **`active_commit.yaml`** file:

```sh
# Copy template active commit file:
cp -v ./templates/configs/active_commit.yaml ./volumes/configs/agent-miner/active_commit.yaml

# Change active commit file with your own commit hash:
nano ./volumes/configs/agent-miner/active_commit.yaml
```

`active_commit.yaml` format:

```yaml
- <CHALLENGE_NAME>---<USERNAME>/<REPO_NAME>@sha256:<DIGEST>
```

For example:

```yaml
- ab_sniffer_v5---my_username/my_repo@sha256:abc123def456...
- ada_detection_v3---my_username/my_repo@sha256:abc123def456...
```

!!! tip "TIP"
    You can add multiple commits for different challenges in the same `active_commit.yaml` file.

!!! warning "WARNING"
    - Only one commit per challenge is allowed in the `active_commit.yaml` file. If you add multiple commits for the same challenge, only the last one will be considered during submission and others will be ignored.
    - We are allowing only one commit per challenge/day for submission to avoid spam, abuse, unnecessary network load, and fair evaluation for all participants.

### 3.2. Configure environment variables

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

### 3.3. Check docker compose configuration

```sh
## Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config
```

### 3.4. Start miner node to submit

```sh
## Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f --tail 100
```

## Step 4: Monitor your miner

### Check Status

```sh
btcli subnet list --netuid 61
btcli subnet show_stake --wallet-name miner --wallet.hotkey default --netuid 61
```

### Track Performance

- Visit the [RedTeam Dashboard](https://dashboard.theredteam.io) to monitor your miner's performance, scores, and earnings.
- Monitor scores and validator feedback
- Optimize solution and resubmit

## Troubleshooting

**Docker permission denied:**

```sh
sudo usermod -aG docker $USER
newgrp docker
```

**Miner not registering:**

```sh
btcli wallet balance --wallet-name miner
btcli subnet show --wallet-name miner --wallet.hotkey default --netuid 61
```

## Next Steps

- **[Challenge Menu](../challenges/README.md)** - Browse available challenges
- **[Building Submissions](../miner/workflow/3.build-and-submit.md)** - Detailed submission guide
- **[Miner Repository](https://github.com/RedTeamSubnet/miner)** - Examples and templates
