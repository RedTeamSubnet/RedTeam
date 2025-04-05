#!/bin/bash
set -euo pipefail


# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi


docker run \
	--rm \
	-it \
	--name bot_container \
	-e HBC_WEB_URL="${HBC_WEB_URL:-https://172.17.0.1:10001/_web}" \
	-e HBC_ACTION_LIST="${HBC_ACTION_LIST}" \
	-e HBC_SESSION_COUNT="${HBC_SESSION_COUNT}" \
	bot:latest
