#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


if ! command -v mkdocs >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'mkdocs' command, please install it first!" >&2
	exit 1
fi

if ! command -v mike >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'mike' command, please install it first!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_BUILD=false
_IS_PUBLISH=false
_IS_CLEAN=true
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -b, --build            Enable build step. Default: false
    -p, --publish          Enable publish step. Default: false
    -c, --disable-clean    Disable clean step. Default: true
    -h, --help             Show this help message.

EXAMPLES:
    ${0} -b -p -c
    ${0} --build
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-b | --build)
			_IS_BUILD=true
			shift;;
		-p | --publish)
			_IS_PUBLISH=true
			shift;;
		-c | --disable-clean)
			_IS_CLEAN=false
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


if [ "${_IS_PUBLISH}" == true ]; then
	if ! command -v git >/dev/null 2>&1; then
		echo "[ERROR]: Not found 'git' command, please install it first!" >&2
		exit 1
	fi

	if [ ! -f ./scripts/get-version.sh ]; then
		echo "[ERROR]: 'get-version.sh' script not found!" >&2
		exit 1
	fi
fi


## --- Main --- ##
main()
{
	local _major_minor_version
	if [ "${_IS_BUILD}" == true ]; then
		echo "[INFO]: Building documentation pages (HTML) into the 'site' directory..."
		mkdocs build

		# _major_minor_version="$(./scripts/get-version.sh | cut -d. -f1-2)"
		# mike deploy -u "${_major_minor_version}" latest
		# mike set-default latest
	elif [ "${_IS_PUBLISH}" == true ]; then
		echo "[INFO]: Publishing documentation pages to the GitHub Pages..."
		# mkdocs gh-deploy --force

		_major_minor_version="$(./scripts/get-version.sh | cut -d. -f1-2)"
		mike deploy -p -u "${_major_minor_version}" latest
		mike set-default -p latest

		if [ "${_IS_CLEAN}" == true ]; then
			if [ ! -f ./scripts/clean.sh ]; then
				echo "[ERROR]: 'clean.sh' script not found!" >&2
				exit 1
			fi

			./scripts/clean.sh || exit 2
		fi
	else
		echo "[INFO]: Starting documentation server..."
		#shellcheck disable=SC2086
		mkdocs serve -a 0.0.0.0:${DOCS_PORT:-8000} --livereload
		# mike serve -a 0.0.0.0:${DOCS_PORT:-8000}
	fi
	echo "[OK]: Done."
}

main
## --- Main --- ##
