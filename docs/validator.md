# Validator Setup

## Minimum System Requirements
Below is the minimum system requirements for running a validator node on the Innerworks Subnet:
- Bare Metal Server
- GPU with 24-GB VRAM
- Ubuntu 20.04 LTS
- NVIDIA Driver
- 32-GB RAM
- 512-GB Storage
- 8-Core CPU

## Setup Instructions
To set up a validator node on the Innerworks Subnet, follow these steps:
1. Install the latest version of the Innerworks Subnet repository.
```bash
git clone https://github.com/SocialTensor/ScriptcuritySubnet && cd ScriptcuritySubnet
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

3. Start the validator node:
```bash
pm2 start python --name "validator_snxxx" \
-- -m neurons.validator.validator \
--netuid xxx \
--wallet.name "wallet_name" \
--wallet.hotkey "wallet_hotkey" \
--subtensor.network finney
```
Optional flags:
- `--logging.trace` - Enable trace logging
- `--logging.debug` - Enable debug logging