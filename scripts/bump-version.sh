#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env


if [ ! -f ./scripts/get-version.sh ]; then
	echo "[ERROR]: 'get-version.sh' script not found!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
VERSION_FILE_PATH="${VERSION_FILE_PATH:-./src/redteam_core/__version__.py}"


_BUMP_TYPE=""

# Flags:
_IS_COMMIT=false
_IS_TAG=false
_IS_PUSH=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -b, --bump-type [TYPE]    Specify version bump type. [major | minor | patch]
    -c, --commit              Create a commit for the bumped version. Default: false
    -t, --tag                 Create a git tag for the bumped version. Default: false
    -p, --push                Push commits and tags to the remote. Default: false
    -h, --help                Show this help message.

EXAMPLES:
    ${0} -b patch -c -t -p
    ${0} --bump-type=minor
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-b | --bump-type)
			[ $# -ge 2 ] || { echo "[ERROR]: ${1} requires a value!" >&2; exit 1; }
			_BUMP_TYPE="${2}"
			shift 2;;
		-b=* | --bump-type=*)
			_BUMP_TYPE="${1#*=}"
			shift;;
		-c | --commit)
			_IS_COMMIT=true
			shift;;
		-t | --tag)
			_IS_TAG=true
			shift;;
		-p | --push)
			_IS_PUSH=true
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


if [ -z "${_BUMP_TYPE:-}" ]; then
	echo "[ERROR]: Bump type is empty, use '-b=' or '--bump-type=' argument!" >&2
	exit 1
fi

if [ "${_BUMP_TYPE}" != "major" ] && [ "${_BUMP_TYPE}" != "minor" ] && [ "${_BUMP_TYPE}" != "patch" ]; then
	echo "[ERROR]: Bump type '${_BUMP_TYPE}' is invalid, should be: 'major', 'minor' or 'patch'!" >&2
	exit 1
fi

if [ "${_IS_COMMIT}" == true ]; then
	if ! command -v git >/dev/null 2>&1; then
		echo "[ERROR]: Not found 'git' command, please install it first!" >&2
		exit 1
	fi
fi


## --- Main --- ##
main()
{
	echo "[INFO]: Checking current version..."
	local _current_version
	_current_version="$(./scripts/get-version.sh)"
	echo "[OK]: Current version: '${_current_version}'"

	# Split the version string into its components:
	local _major _minor _patch
	_major=$(echo "${_current_version}" | cut -d. -f1)
	_minor=$(echo "${_current_version}" | cut -d. -f2)
	_patch=$(echo "${_current_version}" | cut -d. -f3)

	local _new_version=${_current_version}
	# Determine the new version based on the type of bump:
	if [ "${_BUMP_TYPE}" == "major" ]; then
		_new_version="$((_major + 1)).0.0"
	elif [ "${_BUMP_TYPE}" == "minor" ]; then
		_new_version="${_major}.$((_minor + 1)).0"
	elif [ "${_BUMP_TYPE}" == "patch" ]; then
		_new_version="${_major}.${_minor}.$((_patch + 1))"
	fi

	echo "[INFO]: Bumping version to '${_new_version}'..."
	# Update the version file with the new version:
	echo -e "__version__ = \"${_new_version}\"" > "${VERSION_FILE_PATH}" || exit 2
	echo "[OK]: New version: '${_new_version}'"

	if [ "${_IS_COMMIT}" == true ]; then
		echo "[INFO]: Committing bump version 'v${_new_version}'..."
		# Commit the updated version file:
		git add "${VERSION_FILE_PATH}" || exit 2
		git commit -m "version: bump version to '${_new_version}'." || exit 2
		echo "[OK]: Done."

		if [ "${_IS_TAG}" == true ]; then
			echo "[INFO]: Tagging 'v${_new_version}'..."
			if git rev-parse "v${_new_version}" > /dev/null 2>&1; then
				echo "[ERROR]: 'v${_new_version}' tag is already exists!" >&2
				exit 1
			fi
			git tag "v${_new_version}" || exit 2
			echo "[OK]: Done."
		fi

		if [ "${_IS_PUSH}" == true ]; then
			echo "[INFO]: Pushing 'v${_new_version}'..."
			git push || exit 2

			if [ "${_IS_TAG}" == true ]; then
				# shellcheck disable=SC1083
				git push "$(git rev-parse --abbrev-ref --symbolic-full-name @{upstream} | sed 's/\/.*//')" "v${_new_version}" || exit 2
			fi
			echo "[OK]: Done."
		fi
	fi
}

main
## --- Main --- ##
