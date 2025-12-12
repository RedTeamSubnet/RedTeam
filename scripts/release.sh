#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


if ! command -v git >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'git' command, please install it first!" >&2
	exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'gh' command, please install it first!" >&2
	exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
	echo "[ERROR]: You need to login: 'gh auth login'!" >&2
	exit 1
fi

if [ ! -f ./scripts/get-version.sh ]; then
	echo "[ERROR]: 'get-version.sh' script not found!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_BUILD=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -b, --build    Enable build step. Default: false
    -h, --help     Show this help message.

EXAMPLES:
    ${0} -b
    ${0} --build
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-b | --build)
			_IS_BUILD=true
			shift;;
		-h | --help)
			_usage_help
			exit 0;;
		*)
			echo "[ERROR]: Failed to parse argument -> ${1}!" >&2
			_usage_help
			exit 1;;
	esac
done
## --- Menu arguments --- ##


if [ "${_IS_BUILD}" == true ]; then
	if [ ! -f ./scripts/build.sh ]; then
		echo "[ERROR]: 'build.sh' script not found!" >&2
		exit 1
	fi

	./scripts/build.sh -c || exit 2
fi


## --- Main --- ##
main()
{
	local _current_version
	_current_version="$(./scripts/get-version.sh)"
	echo "[INFO]: Creating release for version: 'v${_current_version}'..."
	gh release create "v${_current_version}" ./dist/* --generate-notes
	echo "[OK]: Done."
}

main
## --- Main --- ##
