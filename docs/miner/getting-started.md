---
title: Getting Started
---

# Getting Started

## Step 1: Prepare Your Environment

!!! warning "System Requirements"
    - **CPU**: 2+ cores
    - **RAM**: 8GB minimum
    - **Storage**: 50GB available
    - **OS**: Linux (Ubuntu 22.04 LTS+ recommended)
    - **Network**: Stable internet connection

- Install Prerequisites
    - Docker: [Install Docker](../manuals/installation/docker.md)
    - miniconda: [Install Miniconda](../manuals/installation/miniconda.md)
    - nvm: [Install NVM](../manuals/installation/nvm.md)
    - pm2: [Install PM2](../manuals/installation/pm2.md)
- Set up a wallet: [Wallet Setup Guide](../manuals/bittensor/wallet/README.md)

## Step 2: Create Workspace

```sh
mkdir -pv ~/workspaces/projects/redteam61
cd ~/workspaces/projects/redteam61
python3.10 -m venv redteam
source redteam/bin/activate
```

## Step 3: Clone the Miner Repository

```sh
git clone https://github.com/RedTeamSubnet/miner.git agent-miner
cd agent-miner
```

Repository structure:
- `examples/` - Challenge solutions and templates
- `compose.yml` - Docker Compose configuration
- `pm2-process.json.example` - PM2 configuration

### Step 4: Choose Your Deployment Method

=== "Docker Compose (Recommended)"

    #### Configure Environment

    ```bash
    cp .env.example .env
    nano .env
    ```

    Set your configuration:
    ```env
    WALLET_NAME=miner
    WALLET_HOTKEY=default
    NETUID=61
    SUBTENSOR_NETWORK=finney
    ```

    #### Start Miner

    ```sh
    chmod +x ./compose.sh
    ./compose.sh start -l
    ```

    #### Monitor

    ```sh
    docker compose logs -f
    docker compose ps
    ```
=== "PM2"

    #### Configure

    ```sh
    cp pm2-process.json.example pm2-process.json
    ```

    #### Start Miner

    ```sh
    pm2 start pm2-process.json
    pm2 logs agent-miner
    ```

    #### Manage

    ```sh
    pm2 stop agent-miner
    pm2 restart agent-miner
    pm2 status
    ```

## Step 5: Monitor Your Miner

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
- **[Building Submissions](building-commit.md)** - Detailed submission guide
- **[Miner Repository](https://github.com/RedTeamSubnet/miner)** - Examples and templates
