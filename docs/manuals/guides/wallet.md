---
title: "Bittensor Wallet"
tags: [bittensor, wallet]
---

# :fontawesome-solid-wallet: Bittensor Wallet

This guide walks you through the process of setting up a Bittensor wallet, which is essential for participating in the Bittensor network.

## 🌐 Official Pages

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

### 1. Prerequisites

- Install and open **Terminal** or **Command Line Interface** to run commands.
- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](../installation/miniconda.md)**

### 2. Install Bittensor CLI

First, you need to install the Bittensor CLI (BTCLI) using pip:

```sh
pip install -U bittensor-cli
```

### 3. Create your wallets

#### 3.1. Create a Coldkey

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

#### 3.2. Create a Hotkey

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

### 4. Verify your wallets

```sh
btcli wallet list --verbose

# Or
btcli wallet list --wallet-path <WALLET_PATH>
# For example:
btcli wallet list --wallet-path ~/.bittensor/wallets
```

## 💰 Funding your Wallet

Bittensor wallets need TAO tokens to perform various operations on the network such as paying transaction fees, registering, staking, and participating in consensus.

### 1. Acquire TAO tokens

You can acquire TAO tokens through the following methods.

If you are a new to Bittensor, you need to obtain TAO tokens by:

- **Buy/Exchanges**: TAO tokens can be purchased from exchanges that list them, check **[Coinranking](https://coinranking.com/coin/pgv7xSFi6+bittensor-tao/exchanges)** for a list of supported exchanges.
- **Transfers**: Existing token holders can **transfer TAO to your wallet**.

If you are familiar with Bittensor and already have some TAO tokens, you can earn more TAO tokens by:

- **Mining/Staking**: Participate in mining or staking activities on the Bittensor network to earn TAO tokens as rewards.

For testing and development purposes, you might consider:

- **Faucets/Testnets**: For testing purposes, you can use faucets available on Bittensor testnets to get free TAO tokens. But be aware that these tokens are not valid on the mainnet.

### 2. Check your wallet balance

Once you have TAO tokens in your wallet, you can check your balance using the following commands.

Check all wallet balances:

```sh
btcli wallet balance --all

# Or from a specific wallet path:
btcli wallet balance --wallet-path <WALLET_PATH> --all
# For example:
btcli wallet balance --wallet-path ~/.bittensor/wallets --all
```

Check specific wallet balance:

```sh
btcli wallet balance --wallet-path <WALLET_PATH> --wallet-name <WALLET_NAME>

# For example:
btcli wallet balance --wallet-path ~/.bittensor/wallets --wallet-name my_wallet
```

---

## References

- <https://docs.learnbittensor.org>
