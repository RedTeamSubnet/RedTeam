#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


if ! command -v python >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'python' command, please install it first!" >&2
	exit 1
fi

if ! command -v pytest >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'pytest' command, please install it first!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_LOGGING=false
_IS_COVERAGE=false
_IS_VERBOSE=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -l, --log        Enable logging. Default: false
    -c, --cov        Enable coverage. Default: false
    -v, --verbose    Enable verbose output. Default: false
    -h, --help       Show this help message.

EXAMPLES:
    ${0} -l -c -v
    ${0} --log
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-l | --log)
			_IS_LOGGING=true
			shift;;
		-c | --cov)
			_IS_COVERAGE=true
			shift;;
		-v | --verbose)
			_IS_VERBOSE=true
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


if [ "${_IS_COVERAGE}" == true ]; then
	if ! python -c "import pytest_cov" &> /dev/null; then
		echo "[ERROR]: 'pytest-cov' python package is not installed!" >&2
		exit 1
	fi
fi


## --- Main --- ##
main()
{
	local _logging_param=""
	local _coverage_param=""
	local _verbose_param=""
	if [ "${_IS_LOGGING}" == true ]; then
		_logging_param="-o log_cli=true"
	fi

	if [ "${_IS_COVERAGE}" == true ]; then
		_coverage_param="--cov"
	fi

	if [ "${_IS_VERBOSE}" == true ]; then
		_verbose_param="-svv"
	fi

	echo "[INFO]: Running test..."
	# shellcheck disable=SC2086
	python -m pytest -v ${_coverage_param} ${_logging_param} ${_verbose_param} || exit 2
	echo "[OK]: Done."
}

main
## --- Main --- ##
