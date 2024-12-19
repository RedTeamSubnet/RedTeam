# Miner Setup

## Minimum System Requirements
Below is the minimum system requirements for running a miner node on the RedTeam Subnet:
- 8-GB RAM
- 2-Cores CPU

But you may need more resources for engineering challenges.

## Setup Instructions
To set up a miner node on the RedTeam Subnet, follow these steps:
1. Install the latest version of the RedTeam Subnet repository.
```bash
git clone https://github.com/RedTeamSubnet/RedTeam && cd RedTeam
pip install -e .
```

2. Explore challenges at `redteam_core/challenge_pool/`, build your solution, dockerize it, and push it to Docker Hub. You can view the detailed guide [here](challenge_submission_guide.md). We have some limitations on your solution:
- The solution must be a Python script.
- Allowed to use GPU with 24GB VRAM
- The solution won't be able to access the internet.
- Total size of the solution must be less than 10GB.


2. Specify docker submissions for challenges at `neurons/miner/active_commit.yaml`:
```yaml
- challenge_name_1---docker_hub_id_1@<sha256:digest>
- challenge_name_2---docker_hub_id_2<sha256:digest>
```

3. Start the miner node:
```bash
pm2 start python --name "miner_snxxx" \
-- -m neurons.miner.miner \
--netuid xxx \
--wallet.name "wallet_name" \
--wallet.hotkey "wallet_hotkey" \
--axon.port "axon_port" \
--subtensor.network <network> \ # default is finney
```
Optional flags:
- `--logging.trace` - Enable trace logging
- `--logging.debug` - Enable debug logging