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


if [ -z "$(which python)" ]; then
	echoError "'python' not found or not installed."
	exit 1
fi

if [ -z "$(which pytest)" ]; then
	echoError "'pytest' not found or not installed."
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_LOGGING=false
_IS_COVERAGE=false
_IS_VERBOSE=false
## --- Variables --- ##


## --- Main --- ##
main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-l | --log)
					_IS_LOGGING=true
					shift;;
				-c | --cov)
					_IS_COVERAGE=true
					shift;;
				-v | --verbose)
					_IS_VERBOSE=true
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0}  -l, --log | -c, --cov | -v, --verbose"
					exit 1;;
			esac
		done
	fi
	## --- Menu arguments --- ##


	if [ "${_IS_COVERAGE}" == true ]; then
		if ! python -c "import pytest_cov" &> /dev/null; then
			echoError "'pytest-cov' python package is not installed."
			exit 1
		fi
	fi


	_logging_param=""
	_coverage_param=""
	_verbose_param=""
	if [ "${_IS_LOGGING}" == true ]; then
		_logging_param="-o log_cli=true"
	fi

	if [ "${_IS_COVERAGE}" == true ]; then
		_coverage_param="--cov"
	fi

	if [ "${_IS_VERBOSE}" == true ]; then
		_verbose_param="-svv"
	fi

	echoInfo "Running test..."
	# shellcheck disable=SC2086
	python -m pytest -v ${_coverage_param} ${_logging_param} ${_verbose_param} || exit 2
	echoOk "Done."
}

main "${@:-}"
## --- Main --- ##
