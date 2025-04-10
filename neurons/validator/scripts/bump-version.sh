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

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
VERSION_FILE_PATH="${VERSION_FILE_PATH:-VERSION.txt}"


_BUMP_TYPE=""
## --- Variables --- ##


## --- Main --- ##
main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-b=* | --bump-type=*)
					_BUMP_TYPE="${_input#*=}"
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0} -b=*, --bump-type=* [major | minor | patch]"
					exit 1;;
			esac
		done
	fi
	## --- Menu arguments --- ##


	if [ -z "${_BUMP_TYPE:-}" ]; then
		echoError "Bump type is empty! Use '-b=' or '--bump-type=' argument."
		exit 1
	fi

	if [ "${_BUMP_TYPE}" != "major" ] && [ "${_BUMP_TYPE}" != "minor" ] && [ "${_BUMP_TYPE}" != "patch" ]; then
		echo "Bump type '${_BUMP_TYPE}' is invalid, should be: 'major', 'minor' or 'patch'!"
		exit 1
	fi


	echoInfo "Checking current version..."
	_current_version="$(./scripts/get-version.sh)"
	echoOk "Current version: '${_current_version}'"

	# Split the version string into its components:
	_major=$(echo "${_current_version}" | cut -d. -f1)
	_minor=$(echo "${_current_version}" | cut -d. -f2)
	_patch=$(echo "${_current_version}" | cut -d. -f3 | cut -d- -f1)

	_new_version=${_current_version}
	# Determine the new version based on the type of bump:
	if [ "${_BUMP_TYPE}" == "major" ]; then
		_new_version="$((_major + 1)).0.0-$(date -u '+%y%m%d')"
	elif [ "${_BUMP_TYPE}" == "minor" ]; then
		_new_version="${_major}.$((_minor + 1)).0-$(date -u '+%y%m%d')"
	elif [ "${_BUMP_TYPE}" == "patch" ]; then
		_new_version="${_major}.${_minor}.$((_patch + 1))-$(date -u '+%y%m%d')"
	fi

	echoInfo "Bumping version to '${_new_version}'..."
	# Update the version file with the new version:
	echo "${_new_version}" > "${VERSION_FILE_PATH}" || exit 2
	echoOk "New version: '${_new_version}'"
}

main "${@:-}"
## --- Main --- ##
