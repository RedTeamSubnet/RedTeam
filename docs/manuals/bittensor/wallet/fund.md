---
title: "Fund Your Wallet"
tags: [funding]
---

# 💸 Fund Your Wallet

Bittensor wallets need TAO tokens to perform various operations on the network such as paying transaction fees, registering, staking, and participating in consensus.

## Prerequisites

- [**Bittensor Wallet**](./create.md): You need to have a Bittensor wallet created.

## 1. Acquire TAO tokens into your wallet

You can acquire TAO tokens through the following methods.

If you are a new to Bittensor, you need to obtain TAO tokens by:

- **Buy/Exchanges**: TAO tokens can be purchased from exchanges that list them, check **[Coinranking](https://coinranking.com/coin/pgv7xSFi6+bittensor-tao/exchanges)** for a list of supported exchanges.
- **Transfers**: Existing token holders can **transfer TAO to your wallet**.

If you are familiar with Bittensor and already have some TAO tokens, you can earn more TAO tokens by:

- **Mining/Staking**: Participate in mining or staking activities on the Bittensor network to earn TAO tokens as rewards.

For testing and development purposes, you might consider:

- **Faucets/Testnets**: For testing purposes, you can use faucets available on Bittensor testnets to get free TAO tokens. But be aware that these tokens are not valid on the mainnet.

## 2. Check your wallet balance

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

## 3. Next step

- [Register on Subnet](./register.md)

---

## References
