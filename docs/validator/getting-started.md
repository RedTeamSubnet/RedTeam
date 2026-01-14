---
title: Getting Started
---


## Getting Started

### Step 1: Prepare Your Wallet

!!! info "Skip if you already have a validator wallet"
    If you already have a validator wallet with sufficient stake on the RedTeam subnet, you can proceed to Step 2.

- Install **Bittensor CLI** (`btcli`):
    - [Installing Bittensor CLI](https://docs.learnbittensor.org/getting-started/install-btcli)
- Create validator wallet:
    - [Working with Keys](https://docs.learnbittensor.org/keys/working-with-keys)
- Stake TAO with your validator wallet:
    - [Staker's Guide to BTCLI](https://docs.learnbittensor.org/staking-and-delegation/stakers-btcli-guide)
- Register to RedTeam subnet:
    - [Validator's Guide to BTCLI](https://docs.learnbittensor.org/validators/validators-btcli-guide)

### Step 2: Choose Your Deployment Method

=== "Docker Compose (Recommended)"

    1. Visit the [Validator Repository](https://github.com/RedTeamSubnet/validator)
    2. Follow the setup instructions in the README
    3. Configure `.env` with your wallet details
    4. Run: `./compose.sh start -l`

=== "PM2"

    1. Clone validator repository: `git clone https://github.com/RedTeamSubnet/validator`
    2. Configure PM2: `cp pm2-process.json.example pm2-process.json && nano pm2-process.json`
    3. Run setup script: `./scripts/run.sh`
    4. For detailed instructions, see [Validator Repository](https://github.com/RedTeamSubnet/validator)

### Step 3: Monitor Your Validator

Once running, monitor your validator's performance:

```sh
# Docker Compose
docker compose logs -f

# PM2
pm2 logs validator_sn61
```

Check your validator's performance and VTRUST score on the network.
