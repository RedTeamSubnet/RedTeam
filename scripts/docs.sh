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


if [ -z "$(which mkdocs)" ]; then
	echoError "'mkdocs' not found or not installed."
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_BUILD=false
_IS_PUBLISH=false
## --- Variables --- ##


## --- Main --- ##
main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-b | --build)
					_IS_BUILD=true
					shift;;
				-p | --publish)
					_IS_PUBLISH=true
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0}  -b, --build | -p, --publish"
					exit 1;;
			esac
		done
	fi
	## --- Menu arguments --- ##


	if [ "${_IS_PUBLISH}" == true ]; then
		exitIfNoGit
	fi


	if [ "${_IS_BUILD}" == false ]; then
		echoInfo "Starting documentation server..."
		mkdocs serve
	elif [ "${_IS_PUBLISH}" == true ]; then
		echoInfo "Publishing documentation pages to the GitHub Pages..."
		mkdocs gh-deploy --force
	else
		echoInfo "Building documentation pages (HTML) into the 'site' directory..."
		mkdocs build
	fi
	echoOk "Done."
}

main "${@:-}"
## --- Main --- ##
