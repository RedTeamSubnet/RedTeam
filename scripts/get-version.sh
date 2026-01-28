#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
VERSION_FILE_PATH="${VERSION_FILE_PATH:-./src/redteam_core/__version__.py}"
## --- Variables --- ##


if [ -n "${VERSION_FILE_PATH}" ] && [ -f "${VERSION_FILE_PATH}" ]; then
	_current_version=$(< "${VERSION_FILE_PATH}" grep "__version__ = " | awk -F' = ' '{print $2}' | tr -d '"') || exit 2
else
	_current_version="0.0.0"
fi

echo "${_current_version}"
