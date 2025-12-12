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

if ! python -c "import build" &> /dev/null; then
	echo "[ERROR]: 'build' python package is not installed!" >&2
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


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -c, --disable-clean    Disable clean process. Default: true
    -t, --test             Enable test mode. Default: false
    -u, --upload           Enable upload mode. Default: false
    -p, --production       Disable staging mode. Default: true
    -h, --help             Show this help message.

EXAMPLES:
    ${0} --test
    ${0} -c -u -p
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
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


if [ "${_IS_UPLOAD}" == true ]; then
	if ! command -v twine >/dev/null 2>&1; then
		echo "[ERROR]: Not found 'twine' command, please install it first!" >&2
		exit 1
	fi
fi


if [ "${_IS_CLEAN}" == true ]; then
	if [ ! -f ./scripts/clean.sh ]; then
		echo "[ERROR]: 'clean.sh' script not found!" >&2
		exit 1
	fi

	./scripts/clean.sh || exit 2
fi

if [ "${_IS_TEST}" == true ]; then
	if [ ! -f ./scripts/test.sh ]; then
		echo "[ERROR]: 'test.sh' script not found!" >&2
		exit 1
	fi

	./scripts/test.sh || exit 2
fi


## --- Main --- ##
main()
{
	echo "[INFO]: Building package..."
	# python setup.py sdist bdist_wheel || exit 2
	python -m build || exit 2
	echo "[OK]: Done."

	if [ "${_IS_UPLOAD}" == true ]; then
		echo "[INFO]: Publishing package..."
		python -m twine check dist/* || exit 2
		if [ "${_IS_STAGING}" == true ]; then
			python -m twine upload --repository testpypi dist/* || exit 2
		else
			python -m twine upload dist/* || exit 2
		fi
		echo "[OK]: Done."

		if [ "${_IS_CLEAN}" == true ]; then
			./scripts/clean.sh || exit 2
		fi
	fi
}

main
## --- Main --- ##
