# Validator Setup

## Minimum System Requirements
Below is the minimum system requirements for running a validator node on the RedTeam Subnet:
- Bare Metal Server
- GPU with 24-GB VRAM
- Ubuntu 20.04 LTS
- NVIDIA Driver
- 32-GB RAM
- 512-GB Storage
- 8-Core CPU

## Setup Instructions
To set up a validator node on the RedTeam Subnet, follow these steps:
1. Install the latest version of the RedTeam Subnet repository.
```bash
git clone https://github.com/RedTeamSubnet/RedTeam && cd RedTeam
pip install -e .
```

2. Install Docker Engine (guide from official Docker documentation):
```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

To verify the installation, run:
```bash
sudo docker run hello-world
```

3. Login to Hugging Face Hub
Authenticate your Hugging Face Hub account. Run the following command to log in:
```bash
huggingface-cli login
```
You will be prompted to enter your Hugging Face access token. Visit [Hugging Face Access Tokens](https://huggingface.co/settings/tokens) to generate one if you don't have it already.

4. Custom Setup for Specific Challenges
For setup instructions related to specific challenges, please refer to the [Validator Custom Setup](validator_custom.md).

5. Start the validator node:
```bash
pm2 start python --name "validator_snxxx" \
-- -m neurons.validator.validator \
--netuid xxx \
--wallet.name "wallet_name" \
--wallet.hotkey "wallet_hotkey" \
--subtensor.network <network> \ # default is finney
--validator.cache_dir "./.cache/" \ # Your local cache dir for miners commits.
--validator.hf_repo_id "my_username/my_repo" \ # Your HF repo ID for storing miners' commits. You need to create your own repo; recommend creating a new HF account
--validator.use_centralized_scoring \ # Optional: Recommended for high VTRUST, opt-in to get scores of challenges from a centralized server
```
Optional flags:
- `--logging.trace` - Enable trace logging
- `--logging.debug` - Enable debug logging