---
title: "Bittensor Wallet"
tags: [bittensor, wallet]
---

# :fontawesome-solid-wallet: Bittensor Wallet

This guide walks you through the process of setting up a Bittensor wallet, which is essential for participating in the Bittensor network.

## ✅ Official Pages

Before you begin, we recommend you read truough the Bittensor official documentation pages to understand the concepts and functionalities of Bittensor wallets:

- Bittensor CLI: <https://docs.learnbittensor.org/btcli/overview>
- Install BTCLI: <https://docs.learnbittensor.org/getting-started/install-btcli>
- Bittensor Wallets: <https://docs.learnbittensor.org/keys/wallets>
- Permissions Guide: <https://docs.learnbittensor.org/btcli/btcli-permissions>
- Working with Keys: <https://docs.learnbittensor.org/keys/working-with-keys>
- Miner's Guide to BTCLI: <https://docs.learnbittensor.org/miners/miners-btcli-guide>
- Validator's Guide to BTCLI: <https://docs.learnbittensor.org/validators/validators-btcli-guide>
- Staker's Guide to BTCLI: <https://docs.learnbittensor.org/staking-and-delegation/stakers-btcli-guide>
- BTCLI reference: <https://docs.learnbittensor.org/btcli>

## 🧊 Coldkey vs. 🔥 Hotkey

To participate in the Bittensor network, you need two types of wallets: **Coldkey** and **Hotkey**.

- **Coldkey**: This is a secure, offline wallet used to hold TAO tokens and make important administrative decisions. Think of it as your "savings account."
- **Hotkey**: A wallet used for day-to-day operations like mining. This is more like your "checking account," used for frequent transactions but not for storing large amounts of TAO.

---

## 🛠 Setup your Bittensor Wallet

### Prerequisites

- Install and open **Terminal** or **Command Line Interface** to run commands.
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../installation/miniconda.md)**

### Install Bittensor CLI

First, you need to install the Bittensor CLI (BTCLI) using pip:

```sh
pip install -U bittensor-cli
```

### Create your Bittensor wallet

#### Create a Coldkey wallet

**OPTION A.** Interactively with prompts and password protection:

```sh
btcli wallet new-coldkey
```

!!! danger "IMPORTANT"
    - This command will prompt you to enter a **password** and will generate a **mnemonic phrase** (a series of words) for wallet recovery.
    - Make sure to **remember your password** and **securely store your mnemonic phrase**.
    - Losing these means losing access to your wallet and funds permanently.
    - Ensure that you keep your Coldkey secure and offline.

**OPTION B.** Non-interactively with specified arguments (no password):

!!! note "ARGUMENTS"
    Make sure to replace the placeholders:

    - `<WALLET_NAME>` with your wallet name (e.g., `my_wallet`, `sn61_wallet`, `miner`, `validator`, etc.).
    - `<WALLET_PATH>` with the path where you want to store the wallet (e.g., `~/.bittensor/wallets`).
    - `<NUMBER_WORDS>` can typically be 12, 15, 18, 21, or 24 depending on your security preference.

```sh
btcli wallet new-coldkey \
    --wallet-name <WALLET_NAME> \
    --wallet-path <WALLET_PATH> \
    --no-use-password \
    --n-words <NUMBER_WORDS> \
    --overwrite \
    --verbose

# For example:
btcli wallet new-coldkey \
    --wallet-name my_wallet \
    --wallet-path ~/.bittensor/wallets \
    --no-use-password \
    --n-words 12 \
    --overwrite \
    --verbose
```

#### Create a Hotkey

!!! danger "IMPORTANT"
    - Ensure that you keep your Coldkey secure and offline. The Hotkey should be used for daily operations, while the Coldkey should be stored in a safe place.
    - Never share your Coldkey mnemonic or password with anyone.

```sh
btcli wallet new-hotkey
```

## Funding your Wallet

---

## References

- <https://docs.learnbittensor.org>
