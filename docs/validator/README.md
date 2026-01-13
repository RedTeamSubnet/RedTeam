---
title: Validator
---

# Validator

Welcome to the RedTeam Subnet Validator documentation. This guide will help you understand what validators do and how to run one on the RedTeam network.

!!! info "Main Validator Repository"
    The official validator repository with complete setup instructions is available at

    **[RedTeam Subnet Validator Repository →](https://github.com/RedTeamSubnet/validator)**
    
    This is the primary resource for running a validator node with all necessary documentation, configuration examples, and deployment scripts.

---

## What is a Validator?

Validators are essential participants in the RedTeam Subnet that:

- **Evaluate miners** - Send challenges to miners and assess their responses
- **Assign scores** - Rate miner performance based on quality metrics
- **Maintain consensus** - Work with other validators to ensure network integrity
- **Earn rewards** - Receive TAO emissions proportional to stake and performance

## Prerequisites

Before you begin, ensure you have:

- ✅ A registered Bittensor wallet with sufficient TAO staked
- ✅ Validator wallet registered on the RedTeam subnet
- ✅ A system meeting the [minimum requirements](#minimum-system-requirements)
- ✅ Basic knowledge of Docker or PM2 process management

---

## Minimum System Requirements

!!! warning "System Requirements"
    Below are the minimum system requirements for running a validator node:

    - **Server Type**: Bare Metal Server
    - **CPU**: 8-Core CPU
    - **RAM**: 32 GB
    - **Storage**: 512 GB
    - **OS**: Ubuntu 22.04 LTS or later
    - **GPU** (Optional): NVIDIA GPU with 16GB VRAM or higher
    - **Driver** (Optional): NVIDIA Driver (>= v452.39)

---

## Deployment Options

The RedTeam Subnet supports two primary methods for running validator nodes:

### 🐳 Docker Compose (Production - Recommended)

Docker Compose is the recommended method for production deployments. It provides isolation, automated updates, and easier management.

**For complete setup instructions and advanced configuration, see:**

**[→ Validator Repository README](https://github.com/RedTeamSubnet/validator/blob/main/README.md)**

---

### ⚡ PM2 Process Manager (Development/Advanced)

PM2 is suitable for development, testing, or when you need direct access to the Python environment with custom configurations.

!!! warning "Not Recommended"
    Running a validator with PM2 is not recommended due to limited isolation and absence of auto updater which risks validator to lost VTrust.

**Quick Start:**

```sh
# Clone the validator repository
git clone https://github.com/RedTeamSubnet/validator
cd validator

# Copy and configure PM2 settings
cp pm2-process.json.example pm2-process.json
nano pm2-process.json  # Edit with your wallet details

# Run the setup script
./scripts/run.sh
```

**For complete PM2 setup instructions and configuration options, see:**

**[→ Validator Repository](https://github.com/RedTeamSubnet/validator)**

---

## Quick Comparison

| Feature | Docker Compose | PM2 |
|---------|---|---|
| Recommended for | Production | Development/Custom |
| Setup Complexity | Simple | Moderate |
| Isolation | ✅ Yes | ❌ No |
| Auto-Update | ✅ Yes | ❌ No |
| Auto-restart | ✅ Yes | ✅ Yes |
| Log Management | ✅ Automatic | Manual |
| Monitoring | ✅ Built-in | ✅ PM2 native |
| Resource Limits | ✅ Yes | Limited |

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

---

## Key Resources

- **[Main Validator Repository](https://github.com/RedTeamSubnet/validator)** - Official setup and deployment
- **[RedTeam Documentation](https://docs.theredteam.io)** - Network and subnet information
- **[Bittensor Documentation](https://docs.learnbittensor.org)** - General Bittensor knowledge
- **[Bittensor CLI Guide](https://docs.learnbittensor.org/btcli)** - Wallet and network commands

---

## Important Notes

!!! info "Configuration"
    All configuration for running validators should be done through the official **[Validator Repository](https://github.com/RedTeamSubnet/validator)**, which provides:

    - Complete setup instructions
    - Configuration examples
    - Maintenance guidelines
    - Troubleshooting documentation

---

## Troubleshooting & Support

- 📖 Check the [Validator Repository](https://github.com/RedTeamSubnet/validator) for deployment issues
- 💬 Join the [RedTeam Discord](https://discord.gg/redteam) community for support
- 📚 Review [Bittensor Documentation](https://docs.learnbittensor.org) for wallet and network issues
- 🔧 Check system logs for configuration problems

---

## Next Steps

1. **Prepare your wallet** - Register on RedTeam subnet with sufficient stake
2. **Choose deployment method** - Docker Compose for production or PM2 for development
3. **Follow setup instructions** - Use the [Validator Repository README](https://github.com/RedTeamSubnet/validator/blob/main/README.md)
4. **Monitor performance** - Track your validator's VTRUST score and earnings
5. **Stay updated** - Keep your validator updated with the latest versions
