---
title: "Setup Your Wallet"
tags: [setup]
---

# 🛠 Setup Your Bittensor Wallet

## 1. Prerequisites

- Install and open **Terminal** or **Command Line Interface** to run commands.
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../installation/miniconda.md)**

## 2. Install Bittensor CLI

First, you need to install the Bittensor CLI (BTCLI) using pip:

```sh
pip install -U bittensor-cli
```

## 3. Create your wallets

### 3.1. Create a coldkey

**OPTION A.** Interactively with prompts and password protection:

```sh
btcli wallet new-coldkey
```

!!! danger "SECURITY"
    - This command will prompt you to enter a **password** and will generate a **mnemonic phrase** (a series of words) for wallet recovery.
    - Make sure to **securely store your mnemonic phrase**, as it cannot be recovered if lost (only shown once).
    - Never share your coldkey, mnemonic phrase, or password with anyone.
    - Ensure that you keep your coldkey secure and offline if possible.

**OPTION B.** Non-interactively with specified arguments (no password):

!!! note "Arguments"
    Make sure to replace the placeholders:

    - `<WALLET_PATH>` with the path where you want to store the wallet (e.g., `~/.bittensor/wallets`).
    - `<WALLET_NAME>` with your wallet name (e.g., `my_wallet`, `sn61_wallet`, `miner`, `validator`, `default`, etc.).
    - `<NUMBER_WORDS>` can typically be 12, 15, 18, 21, or 24 depending on your security preference.

```sh
btcli wallet new-coldkey \
    --wallet-path <WALLET_PATH> \
    --wallet-name <WALLET_NAME> \
    --n-words <NUMBER_WORDS> \
    --no-use-password \
    --overwrite \
    --verbose

# For example:
btcli wallet new-coldkey \
    --wallet-name my_wallet \
    --wallet-path ~/.bittensor/wallets \
    --n-words 12 \
    --no-use-password \
    --overwrite \
    --verbose
```

### 3.2. Create a hotkey

!!! warning "IMPORTANT"
    - Hotkey is linked to the coldkey, so ensure you have created the coldkey first.
    - Make sure to use the same **wallet name** and **wallet path** as your coldkey when creating the hotkey.
    - Your hotkey will be stored on your system and used for frequent operations like mining, validating, etc.

**OPTION A.** Interactively with prompts:

```sh
btcli wallet new-hotkey
```

**OPTION B.** Non-interactively with specified arguments:

!!! note "Arguments"
    Make sure to replace the placeholders:

    - `<WALLET_PATH>` with the path where you want to store the wallet (e.g., `~/.bittensor/wallets`).
    - `<WALLET_NAME>` with your wallet name (e.g., `my_wallet`, `sn61_wallet`, `miner`, `validator`, `default`, etc.).
    - `<HOTKEY_NAME>` with your hotkey name (e.g., `my_hotkey`, `hot_key1`, `hot_key2`, `default` etc.).
    - `<NUMBER_WORDS>` can typically be 12, 15, 18, 21, or 24 depending on your security preference.

```sh
btcli wallet new-hotkey \
    --wallet-path <WALLET_PATH> \
    --wallet-name <WALLET_NAME> \
    --wallet-hotkey <HOTKEY_NAME> \
    --n-words <NUMBER_WORDS> \
    --overwrite \
    --verbose

# For example:
btcli wallet new-hotkey \
    --wallet-name my_wallet \
    --wallet-path ~/.bittensor/wallets \
    --wallet-hotkey my_hotkey \
    --n-words 12 \
    --overwrite \
    --verbose
```

!!! tip "Multiple Hotkeys"
    You can create multiple hotkeys for a single coldkey if needed.

## 4. Verify your wallets

```sh
btcli wallet list --verbose

# Or
btcli wallet list --wallet-path <WALLET_PATH>
# For example:
btcli wallet list --wallet-path ~/.bittensor/wallets
```

## 5. Next Step

- [Fund Your Wallet](./fund.md)

---

## References
