---
title: 2. Setup Bittensor Wallet
tags: [wallet, bittensor]
---

# 2. Setup Bittensor Wallet

## Install Bittensor CLI

```sh
pip install -U bittensor-cli
```

## Create your Bittensor wallet

```sh
btcli wallet new-coldkey \
    --wallet-name <WALLET_NAME> \
    --wallet-path <WALLET_PATH> \
    --no-use-password \
    --n-words 12 \
    --overwrite \
    --verbose

# For example:
btcli wallet new-coldkey \
    --wallet-name miner \
    --wallet-path ~/.bittensor/wallets \
    --no-use-password \
    --n-words 12 \
    --overwrite \
    --verbose
```
