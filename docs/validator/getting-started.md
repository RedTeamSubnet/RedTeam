---
title: Getting Started
---


## Getting Started

### Step 1: Prepare Your Wallet

!!! info "Skip if you already have a validator wallet"
    If you already have a validator wallet with sufficient stake on the RedTeam subnet, you can proceed to **Step 2**.

    - Set up a wallet using **[btcli instructions](../manuals/bittensor/wallet/README.md)**
    - Stake sufficient TAO to your validator wallet on the RedTeam subnet

### Step 2: Choose Your Deployment Method

=== "Docker Compose (Recommended)"

    1. Visit the [Validator Repository](https://github.com/RedTeamSubnet/validator)
    2. Follow the setup instructions in the README
    3. Configure `.env` with your wallet details
    4. Run: `./compose.sh start -l`

=== "PM2"

    1. Clone validator repository: `git clone https://github.com/RedTeamSubnet/validator`
    2. Configure PM2: `cp pm2-process.json.example pm2-process.json && nano pm2-process.json`
    3. Run setup script: `pm2 start pm2-process.json`
    4. For detailed instructions, see [Validator Repository](https://github.com/RedTeamSubnet/validator)

### Step 3: Monitor Your Validator

Once running, monitor your validator's performance:

```sh
# Docker Compose
docker compose logs -f

# PM2
pm2 logs agent-validator
```

Check your validator's performance and VTRUST score on the network.
