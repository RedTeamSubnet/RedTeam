---
title: Validator
tags:
    - validator
---

# Getting Started - Validator

## Step 1: Prepare Your Environment

!!! warning inline end "System Requirements"
    - **Server Type**: Bare Metal Server
    - **CPU**: 8-Core CPU
    - **RAM**: 32 GB
    - **Storage**: 512 GB
    - **OS**: Ubuntu 22.04 LTS or later

- Install Prerequisites
    - Docker: [Install Docker](../manuals/installation/docker.md)
    - miniconda: [Install Miniconda](../manuals/installation/miniconda.md)
    - nvm: [Install NVM](../manuals/installation/nvm.md)
    - pm2: [Install PM2](../manuals/installation/pm2.md)
- Set up a wallet: [Wallet Setup Guide](../manuals/bittensor/wallet/README.md)

## Step 2: Clone the Validator Repository

```bash
git clone https://github.com/RedTeamSubnet/validator.git agent-validator
cd agent-validator
```

**Repository structure:**

- `src/validator` - Validator source code
- `templates` - Configuration templates
- `compose.yml` - Docker Compose configuration
- `pm2-process.json.example` - PM2 configuration

## Step 3: Choose Your Deployment Method

=== "Docker Compose (Recommended)"

    1. Follow the setup instructions in the `README.md`
    2. Configure 

        ```bash
        cp pm2-process.json.example pm2-process.json
        cp .env.example .env
        ```
    
    3. Set your configuration in `.env`:

        ```bash
        RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets"
        RT_VALIDATOR_WALLET_NAME="validator"
        RT_VALIDATOR_HOTKEY_NAME="default"
        ```
    4. Run: 

        ```bash
        ./compose.sh start -l
        # Alternative: docker compose up -d
        ``` 
=== "PM2"

    1. Configure: 

        ```bash
        cp pm2-process.json.example pm2-process.json 
        cp .env.example .env
        ```
    2. Set your configuration in `.env`:

        ```bash
        RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets"
        RT_VALIDATOR_WALLET_NAME="validator"
        RT_VALIDATOR_HOTKEY_NAME="default"
        ```
    3. Run PM2: 

        ```bash
        pm2 start pm2-process.json
        ```
    4. For detailed instructions, see [Validator Repository](https://github.com/RedTeamSubnet/validator)

## Step 4: Monitor Your Validator

Once running, monitor your validator's performance:

```sh
# Docker Compose
docker compose logs -f

# PM2
pm2 logs agent-validator
```

Check your validator's performance and VTRUST score on the network.
