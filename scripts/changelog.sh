#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env


if ! command -v gh >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'gh' command, please install it first!" >&2
	exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "[ERROR]: You need to login: 'gh auth login'!" >&2
    exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
CHANGELOG_FILE_PATH="${CHANGELOG_FILE_PATH:-./CHANGELOG.md}"
RELEASE_NOTES_FILE_PATH="${RELEASE_NOTES_FILE_PATH:-./docs/release-notes.md}"

# Flags:
_IS_COMMIT=false
_IS_PUSH=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -c, --commit    Enable commit step. Default: false
    -p, --push      Enable push step. Default: false
    -h, --help      Show this help message.

EXAMPLES:
    ${0} -c -p
    ${0} --commit
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-c | --commit)
			_IS_COMMIT=true
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


if [ "${_IS_COMMIT}" == true ]; then
	if ! command -v git >/dev/null 2>&1; then
		echo "[ERROR]: Not found 'git' command, please install it first!" >&2
		exit 1
	fi
fi


## --- Main --- ##
main()
{
	local _changelog_title="# Changelog"
	local _release_tag _release_notes _release_entry
	_release_tag=$(gh release view --json tagName -q ".tagName")
	_release_notes=$(gh release view --json body -q ".body")
	_release_entry="## ${_release_tag} ($(date '+%Y-%m-%d'))\n\n${_release_notes}"

	echo "[INFO]: Updating changelog..."
	if ! grep -q "^${_changelog_title}" "${CHANGELOG_FILE_PATH}"; then
		echo -e "${_changelog_title}\n\n" > "${CHANGELOG_FILE_PATH}"
	fi

	local _tail_changelog
	_tail_changelog=$(tail -n +3 "${CHANGELOG_FILE_PATH}")
	echo -e "${_changelog_title}\n\n${_release_entry}\n\n${_tail_changelog}" > "${CHANGELOG_FILE_PATH}"
	echo "[OK]: Updated changelog version: '${_release_tag}'"


	echo "[INFO]: Updating release notes..."
	local _release_notes_header="---\ntitle: Release Notes\nhide:\n  - navigation\n---\n\n# 📌 Release Notes"
	if ! grep -q "^# 📌 Release Notes" "${RELEASE_NOTES_FILE_PATH}"; then
		echo -e "${_release_notes_header}\n\n" > "${RELEASE_NOTES_FILE_PATH}"
	fi

	local _tail_notes
	_tail_notes=$(tail -n +9 "${RELEASE_NOTES_FILE_PATH}")
	echo -e "${_release_notes_header}\n\n${_release_entry}\n\n${_tail_notes}" > "${RELEASE_NOTES_FILE_PATH}"
	echo "[OK]: Updated release notes with version: '${_release_tag}'"

	if [ "${_IS_COMMIT}" == true ]; then
		echo "[INFO]: Committing changelog version '${_release_tag}'..."
		git add "${CHANGELOG_FILE_PATH}" || exit 2
		git add "${RELEASE_NOTES_FILE_PATH}" || exit 2
		git commit -m "docs: update changelog version '${_release_tag}'." || exit 2
		echo "[OK]: Done."

		if [ "${_IS_PUSH}" == true ]; then
			echo "[INFO]: Pushing '${_release_tag}'..."
			git push || exit 2
			echo "[OK]: Done."
		fi
	fi
}

main
## --- Main --- ##
