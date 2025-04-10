#!/bin/bash
set -euo pipefail


## --- Base --- ##
# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading base script:
# shellcheck disable=SC1091
source ./scripts/base.sh

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_ALL=false
## --- Variables --- ##


## --- Main --- ##
main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-a | --all)
					_IS_ALL=true
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0}  -a, --all"
					exit 1;;
			esac
		done
	fi
	## --- Menu arguments --- ##


	echoInfo "Cleaning..."

	find . -type f -name ".DS_Store" -print -delete || exit 2
	find . -type f -name ".Thumbs.db" -print -delete || exit 2
	find . -type f -name ".coverage*" -print -delete || exit 2

	find . -type d -name ".benchmarks" -exec rm -rfv {} + || exit 2
	find . -type d -name ".pytest_cache" -exec rm -rfv {} + || exit 2

	rm -rfv "./tmp" || exit 2

	_is_docker_running=false
	if [ -n "$(which docker)" ] && docker info > /dev/null 2>&1; then
		_is_docker_running=true
	fi

	if [ "${_is_docker_running}" == true ]; then
		if docker compose ps | grep 'Up' > /dev/null 2>&1; then
			echoWarn "Docker is running, please stop it before cleaning."
			exit 1
		fi
	fi

	find . -type d -name "__pycache__" -exec rm -rfv {} + || exit 2
	find . -type d -name ".git" -prune -o -type d -name "logs" -exec rm -rfv {} + || exit 2

	if [ "${_IS_ALL}" == true ]; then
		if [ "${_is_docker_running}" == true ]; then
			docker compose down -v --remove-orphans || exit 2
		fi

		rm -rfv ./build || exit 2
		rm -rfv ./dist || exit 2
		rm -rfv ./site || exit 2
		find . -type d -name "*.egg-info" -exec rm -rfv {} + || exit 2

		rm -rfv "./data" || exit 2
		rm -rfv "./volumes/storage/server.subtensor/data" || {
			sudo rm -rfv "./volumes/storage/server.subtensor/data" || exit 2
		}
		rm -rfv "./volumes/storage/sidecar.btcli/data" || exit 2
		rm -rfv "./volumes/storage/agent.validator/data" || exit 2
		rm -rfv "./volumes/storage/agent.miner/data" || exit 2
		rm -rfv "./volumes/storage/server.reward-validator/data" || exit 2
	fi

	echoOk "Done."
}

main "${@:-}"
## --- Main --- ##
