#!/bin/bash
set -euo pipefail


echo "INFO: Running '${RT_REWARD_APP_SLUG}' docker-entrypoint.sh..."

_doStart()
{
	_i=0
	while true; do
		if [ -d "${RT_BTCLI_WALLET_DIR:-${RT_BTCLI_DATA_DIR:-/var/lib/sidecar.btcli}/wallets}" ]; then
			break
		fi

		echo "INFO: Waiting for the wallet directory to be created..."
		_i=$((_i + 1))
		if [ "${_i}" -ge 60 ]; then
			echo "ERROR: Timeout waiting for the wallet directory to be created!"
			exit 1
		fi

		sleep 1
	done

	if [ "${ENV:-}" != "PRODUCTION" ] && [ "${ENV:-}" != "STAGING" ]; then
		_i=0
		while true; do
			local _checkpoint_file_path="${RT_BTCLI_DATA_DIR:-/var/lib/sidecar.btcli}/${RT_BTCLI_CHECKPOINT_FNAME:-.checkpoint.txt}"
			if [ -f "${_checkpoint_file_path}" ]; then
				local _checkpoint_val=0
				_checkpoint_val=$(cat "${_checkpoint_file_path}")
				if [ "${_checkpoint_val}" -ge 4 ]; then
					break
				fi
			fi

			if [ $(( _i % 10 )) -eq 0 ]; then
				echo "INFO: Waiting for the wallets to be registered and ready..."
			fi
			_i=$((_i + 1))
			sleep 1
		done
	fi

	echo "INFO: Starting ${RT_REWARD_APP_SLUG}..."
	exec sg docker "exec python -u ./services/rewarding/app.py \
		--wallet.name \"${RT_REWARD_APP_WALLET_NAME:-validator}\" \
		--wallet.path \"${RT_BTCLI_WALLET_DIR:-${RT_BTCLI_DATA_DIR:-/var/lib/sidecar.btcli}/wallets}\" \
		--wallet.hotkey \"default\" \
		--subtensor.network \"${RT_BT_SUBTENSOR_NETWORK:-${RT_BT_SUBTENSOR_WS_SCHEME:-ws}://${RT_BT_SUBTENSOR_HOST:-subtensor}:${RT_BT_SUBTENSOR_WS_PORT:-9944}}\" \
		--network \"${RT_SUBTENSOR_NETWORK:-test}\" \
		--netuid \"${RT_BT_SUBNET_NETUID:-2}\" \
		--reward_app.port \"${RT_REWARD_APP_PORT:-47920}\" \
		--reward_app.epoch_length \"${RT_REWARD_APP_EPOCH_LENGTH:-60}\" \
		--validator.cache_dir \"${RT_REWARD_APP_DATA_DIR:-/var/lib/server.reward-app}/.cache\" \
		--validator.hf_repo_id \"${RT_REWARD_APP_HF_REPO:-redteamsubnet61/server.reward-app}\"" || exit 2

	exit 0
}


main()
{
	umask 0002 || exit 2
	find "${RT_HOME_DIR}" "${RT_REWARD_APP_DATA_DIR}" "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -path "*/modules" -prune -o -name ".env" -o -print0 | sudo xargs -0 chown -c "${USER}:${GROUP}" || exit 2
	find "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" -type d -not -path "*/modules/*" -not -path "*/scripts/*" -exec sudo chmod 770 {} + || exit 2
	find "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" -type f -not -path "*/modules/*" -not -path "*/scripts/*" -not -name "*.sh" -exec sudo chmod 660 {} + || exit 2
	find "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" -type d -not -path "*/modules/*" -not -path "*/scripts/*" -exec sudo chmod ug+s {} + || exit 2
	find "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -type d -exec sudo chmod 775 {} + || exit 2
	find "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -type f -exec sudo chmod 664 {} + || exit 2
	find "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -type d -exec sudo chmod +s {} + || exit 2
	chmod ug+x "${RT_REWARD_APP_DIR}/services/rewarding/app.py" || exit 2
	# echo "${USER} ALL=(ALL) ALL" | sudo tee -a "/etc/sudoers.d/${USER}" > /dev/null || exit 2
	echo ""

	## Parsing input:
	case ${1:-} in
		"" | -s | --start | start | --run | run)
			_doStart;;
			# shift;;
		-b | --bash | bash | /bin/bash)
			shift
			if [ -z "${*:-}" ]; then
				echo "INFO: Starting bash..."
				/bin/bash
			else
				echo "INFO: Executing command -> ${*}"
				exec /bin/bash -c "${@}" || exit 2
			fi
			exit 0;;
		*)
			echo "ERROR: Failed to parsing input -> ${*}"
			echo "USAGE: ${0}  -s, --start, start | -b, --bash, bash, /bin/bash"
			exit 1;;
	esac
}

main "${@:-}"
