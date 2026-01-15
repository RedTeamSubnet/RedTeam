---
title: "Register on Subnet"
tags: [registration, subnet]
---

# 📝 Register on RedTeam Subnet 61

## Prerequisites

- [**Funded Wallet**](./wallet/fund.md): Ensure you have a Bittensor wallet funded with sufficient TAO tokens to cover the [**registration cost of subnet 61**](https://taostats.io/subnets/61/registration).

## 1. Register your wallet on subnet

**OPTION A.** Interactively with prompts:

```sh
btcli subnet register
```

**OPTION B.** Non-interactively with specified arguments:

!!! note "Arguments"
    Make sure to replace the placeholders:

    - `<WALLET_PATH>` with the path where you want to store the wallet (e.g., `~/.bittensor/wallets`).
    - `<WALLET_NAME>` with your wallet name (e.g., `my_wallet`, `sn61_wallet`, `miner`, `validator`, `default`, etc.).
    - `<HOTKEY_NAME>` with your hotkey name (e.g., `my_hotkey`, `hot_key1`, `hot_key2`, `default` etc.).
    - `<SUBNET_NETUID>` with the netuid of the subnet you want to register on (for **RedTeam subnet**, use `61`).
    - `--yes` to automatically confirm the registration transaction.

```sh
btcli subnet register \
    --wallet-path <WALLET_PATH> \
    --wallet-name <WALLET_NAME> \
    --wallet-hotkey <HOTKEY_NAME> \
    --netuid <SUBNET_NETUID> \
    --verbose \
    --yes

# For example:
btcli subnet register \
    --wallet-path ~/.bittensor/wallets \
    --wallet-name my_wallet \
    --wallet-hotkey my_hotkey \
    --netuid 61 \
    --verbose \
    --yes
```

!!! info "Notes"
    - It may take a few moments for the registration to be processed on the network.
    - The registration cost is effectively burnt once you have successfully registered.

## 2. Verify your registration

**OPTION A.** Check overall all wallets:

```sh
btcli wallet overview
```

**OPTION B.** Check specific wallet and subnet:

```sh
btcli wallet overview \
    --wallet-path <WALLET_PATH> \
    --wallet-name <WALLET_NAME> \
    --wallet-hotkey <HOTKEY_NAME> \
    --netuid <SUBNET_NETUID> \
    --verbose

# For example:
btcli wallet overview \
    --wallet-path ~/.bittensor/wallets \
    --wallet-name my_wallet \
    --wallet-hotkey my_hotkey \
    --netuid 61 \
    --verbose
```

## 3. Next steps

- [Miner](../../miner/README.md)
- [Validator](../../validator/README.md)

---

## References
