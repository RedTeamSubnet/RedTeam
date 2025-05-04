#!/bin/bash
set -euo pipefail


## --- Base --- ##
# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading base script:
# shellcheck disable=SC1091
source ./scripts/base.sh


if [ -z "$(which python)" ]; then
	echoError "'python' not found or not installed."
	exit 1
fi

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi
## --- Base --- ##


python -m neurons.miner.miner \
	--wallet.name "${RT_MINER_WALLET_NAME:-miner}" \
	--wallet.path "${RT_BTCLI_WALLET_DIR:-${RT_BTCLI_DATA_DIR:-/var/lib/sidecar.btcli}/wallets}" \
	--wallet.hotkey "default" \
	--subtensor.network "${RT_BT_SUBTENSOR_NETWORK:-ws://${RT_BT_SUBTENSOR_HOST:-subtensor}:${RT_BT_SUBTENSOR_WS_PORT:-9944}}" \
	--netuid "${RT_BT_SUBNET_NETUID:-2}" \
	--axon.port "${RT_MINER_PORT:-8088}" || exit 2
