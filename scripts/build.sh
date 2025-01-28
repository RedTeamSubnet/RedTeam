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

if ! python -c "import build" &> /dev/null; then
	echoError "'build' python package is not installed."
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_CLEAN=true
_IS_TEST=false
_IS_UPLOAD=false
_IS_STAGING=true
## --- Variables --- ##


## --- Main --- ##
main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-c | --disable-clean)
					_IS_CLEAN=false
					shift;;
				-t | --test)
					_IS_TEST=true
					shift;;
				-u | --upload)
					_IS_UPLOAD=true
					shift;;
				-p | --production)
					_IS_STAGING=false
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0}  -c, --disable-clean | -t, --test | -u, --upload | -p, --production"
					exit 1;;
			esac
		done
	fi
	## --- Menu arguments --- ##


	if [ "${_IS_UPLOAD}" == true ]; then
		if [ -z "$(which twine)" ]; then
			echoError "'twine' not found or not installed."
			exit 1
		fi
	fi


	if [ "${_IS_CLEAN}" == true ]; then
		./scripts/clean.sh || exit 2
	fi

	if [ "${_IS_TEST}" == true ]; then
		./scripts/test.sh || exit 2
	fi


	echoInfo "Building package..."
	# python setup.py sdist bdist_wheel || exit 2
	python -m build || exit 2
	echoOk "Done."

	if [ "${_IS_UPLOAD}" == true ]; then
		echoInfo "Publishing package..."
		python -m twine check dist/* || exit 2
		if [ "${_IS_STAGING}" == true ]; then
			python -m twine upload --repository testpypi dist/* || exit 2
		else
			python -m twine upload dist/* || exit 2
		fi
		echoOk "Done."

		if [ "${_IS_CLEAN}" == true ]; then
			./scripts/clean.sh || exit 2
		fi
	fi
}

main "${@:-}"
## --- Main --- ##
