# Setup for validator

Make sure that you have a registered hotkey to Subnet 23 and stake > 10000 TAO. If you haven't done so, please refer to https://docs.bittensor.com/subnets/register-validate-mine

## Step by Step Guide

1. Git clone and install requirements
```bash
git clone https://github.com/NicheTensor/NicheImage
cd NicheImage
python -m venv main_env
source main_env/bin/activate
pip install -e .
pip uninstall uvloop -y
```

2. Start Validate
```bash
pm2 start python --name "validator_nicheimage" \
-- -m neurons.validator.validator \
--netuid 23 \
--wallet.name <wallet_name> --wallet.hotkey <wallet_hotkey> \
--axon.port <your_public_port> \
--proxy.port <other_public_port> # Optional, pass if you want allow queries through your validator and get paid
--share_response # Optional, sharing miner's response and get paid, require a good bandwidth
--subtensor.network <network> \
```
If you want to run validation APIs locally, check out [Setup validator endpoint](validator_endpoint.md)

3. (Optional) **Enable Auto Update Validator**
```
pm2 start auto_update.sh --name "auto-update"
```