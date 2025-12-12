#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_ALL=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -a, --all     Enable all mode. Default: false
    -h, --help    Show this help message.

EXAMPLES:
    ${0} -a
    ${0} --all
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-a | --all)
			_IS_ALL=true
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


## --- Main --- ##
main()
{
	echo "[INFO]: Cleaning..."

	find . -type f -name ".DS_Store" -print -delete || exit 2
	find . -type f -name ".Thumbs.db" -print -delete || exit 2
	find . -type f -name ".coverage*" -print -delete || exit 2

	find . -type d -name "__pycache__" -exec rm -rfv {} + || exit 2
	find . -type d -name ".benchmarks" -exec rm -rfv {} + || exit 2
	find . -type d -name ".pytest_cache" -exec rm -rfv {} + || exit 2

	find . -type d -name ".git" -prune -o -type d -name "logs" -exec rm -rfv {} + || exit 2

	if [ "${_IS_ALL}" == true ]; then
		rm -rfv ./build || exit 2
		rm -rfv ./dist || exit 2
		rm -rfv ./site || exit 2
		find . -type d -name "*.egg-info" -exec rm -rfv {} + || exit 2
	fi

	echo "[OK]: Done."
}

main
## --- Main --- ##
