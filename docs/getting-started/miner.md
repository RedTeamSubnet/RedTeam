# Getting Started for Miners

## Step 1: Prepare Your Environment

???+ warning inline end "System Requirements"
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
- Solve challenges: [Challenges list](../challenges/README.md)
- Build your submission commits: [Building Submissions](../miner/workflow/3.build-and-submit.md)

## Step 2: Clone the Miner Repository

```bash
git clone https://github.com/RedTeamSubnet/miner.git agent-miner
cd agent-miner
```

Repository structure:

- `compose.yml` - Docker Compose configuration
- `pm2-process.json.example` - PM2 configuration

### Step 3: Choose Your Deployment Method

=== "Docker Compose (Recommended)"

    #### Configure Environment

    ```bash
    cp -v ./templates/configs/active_commit.yaml ./volumes/configs/agent-miner/active_commit.yaml
    cp .env.example .env
    ```
    #### Put your commit hash in `active_commit.yaml`

    ```yaml
    ab_sniffer_v5---your_docker_hub_repository@sha256:your_image_digest
    [...]
    ```

    ### Set your configuration in `.env`:
    ```env
    RT_MINER_WALLET_NAME="miner" 
    RT_MINER_HOTKEY_NAME="default"
    RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets"
    ```

    #### Start Miner Node

    ``` bash
    chmod +x ./compose.sh
    ./compose.sh start -l # alternative: docker compose up -d
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
    cp .env.example .env
    ```
    
    #### Put your commit hash in `active_commit.yaml`

    ```yaml
    ab_sniffer_v5---your_docker_hub_repository@sha256:your_image_digest
    [...]
    ```
    
    ### Set your configuration in `.env`:
    ```bash
    RT_MINER_WALLET_NAME="miner" 
    RT_MINER_HOTKEY_NAME="default"
    RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets"
    ```

    #### Start Miner Node

    ```bash
    pm2 start pm2-process.json
    pm2 logs agent-miner
    ```

    #### Manage

    ```sh
    pm2 stop agent-miner
    pm2 restart agent-miner
    pm2 status
    ```

## Step 4: Monitor Your Miner

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
