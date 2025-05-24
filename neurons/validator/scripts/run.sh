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


_use_centralized_param=""
if [ "${RT_VALIDATOR_USE_CENTRALIZED:-}" = "true" ]; then
	_use_centralized_param="--validator.use_centralized_scoring"
fi

_logging_param=""
if [ "${RT_VALIDATOR_LOG_LEVEL:-}" = "debug" ]; then
	_logging_param="--logging.debug"
elif [ "${RT_VALIDATOR_LOG_LEVEL:-}" = "trace" ]; then
	_logging_param="--logging.trace"
fi

python -m neurons.validator.validator \
		--wallet.name "${RT_VALIDATOR_WALLET_NAME:-validator}" \
		--wallet.path "${RT_BTCLI_WALLET_DIR:-${RT_BTCLI_DATA_DIR:-/var/lib/sidecar.btcli}/wallets}" \
		--wallet.hotkey "default" \
		--subtensor.network "${RT_BT_SUBTENSOR_NETWORK:-${RT_BT_SUBTENSOR_WS_SCHEME:-ws}://${RT_BT_SUBTENSOR_HOST:-subtensor}:${RT_BT_SUBTENSOR_WS_PORT:-9944}}" \
		--netuid "${RT_BT_SUBNET_NETUID:-2}" \
		--validator.cache_dir "${RT_VALIDATOR_DATA_DIR:-/var/lib/agent.validator}/.cache" \
		--validator.hf_repo_id "${RT_VALIDATOR_HF_REPO:-redteamsubnet61/agent.validator}" \
		${_use_centralized_param} \
		${_logging_param} || exit 2
