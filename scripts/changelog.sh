#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env

# Initialize USE_COMMIT_ANALYSIS before using it
USE_COMMIT_ANALYSIS="${USE_COMMIT_ANALYSIS:-true}"

# Source utility libraries for commit analysis
if [ "${USE_COMMIT_ANALYSIS}" == "true" ]; then
    # shellcheck source=./lib/commit-collector.sh
    source "${_SCRIPT_DIR}/lib/commit-collector.sh"
    # shellcheck source=./lib/gemini-client.sh
    source "${_SCRIPT_DIR}/lib/gemini-client.sh"
fi


if ! command -v gh >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'gh' command, please install it first!" >&2
	exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "[ERROR]: You need to login: 'gh auth login'!" >&2
    exit 1
fi

# Check for required tools for commit analysis
if [ "${USE_COMMIT_ANALYSIS}" == "true" ]; then
    if ! command -v jq >/dev/null 2>&1; then
        echo "[ERROR]: 'jq' is required for commit analysis. Install it or use --use-pr-only" >&2
        exit 1
    fi
    if ! command -v curl >/dev/null 2>&1; then
        echo "[ERROR]: 'curl' is required for commit analysis. Install it or use --use-pr-only" >&2
        exit 1
    fi
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
CHANGELOG_FILE_PATH="${CHANGELOG_FILE_PATH:-./CHANGELOG.md}"
RELEASE_NOTES_FILE_PATH="${RELEASE_NOTES_FILE_PATH:-./docs/release-notes.md}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-pro}"

# Flags:
_IS_COMMIT=false
_IS_PUSH=false
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -c, --commit         Enable commit step. Default: false
    -p, --push           Enable push step. Default: false
    --use-pr-only        Use only PR-based changelog (legacy mode)
    --use-commits        Use commit analysis with LLM (default)
    -h, --help           Show this help message.

ENVIRONMENT:
    GEMINI_API_KEY       Required for commit analysis mode
    USE_COMMIT_ANALYSIS  Enable/disable commit analysis (default: true)

EXAMPLES:
    ${0} -c -p                    # Generate using commits + LLM, commit and push
    ${0} --use-pr-only -c         # Use legacy PR-only mode
    ${0} --commit                 # Generate and commit only
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
		--use-pr-only)
			USE_COMMIT_ANALYSIS=false
			shift;;
		--use-commits)
			USE_COMMIT_ANALYSIS=true
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

# Generate changelog using PR-based method (legacy)
generate_pr_changelog() {
    local _release_tag _release_notes
    _release_tag=$(gh release view --json tagName -q ".tagName")
    _release_notes=$(gh release view --json body -q ".body")
    echo "## ${_release_tag} ($(date '+%Y-%m-%d'))"
    echo ""
    echo "${_release_notes}"
}

# Generate changelog using commit analysis
generate_commit_changelog() {
    echo "[INFO]: Collecting commit data for analysis..." >&2
    
    local commits_data
    commits_data=$(collect_commit_data "${_PROJECT_DIR}")
    
    if [ -z "${commits_data}" ]; then
        echo "[WARN]: No commits found since last release, falling back to PR method" >&2
        generate_pr_changelog
        return 0
    fi
    
    get_commit_stats "${commits_data}"
    
    # Try to generate changelog with Gemini
    if [ -n "${GEMINI_API_KEY}" ]; then
        echo "[INFO]: Generating changelog with Gemini AI..." >&2
        local ai_changelog
        if ai_changelog=$(generate_changelog_with_gemini "${commits_data}"); then
            local _release_tag
            _release_tag=$(gh release view --json tagName -q ".tagName" 2>/dev/null || echo "Unreleased")
            echo "## ${_release_tag} ($(date '+%Y-%m-%d'))"
            echo ""
            echo "${ai_changelog}"
            return 0
        else
            echo "[WARN]: AI generation failed, using fallback method" >&2
        fi
    else
        echo "[WARN]: GEMINI_API_KEY not set, using fallback method" >&2
    fi
    
    # Fallback to simple commit list
    echo "[INFO]: Generating simple changelog from commits..." >&2
    local _release_tag
    _release_tag=$(gh release view --json tagName -q ".tagName" 2>/dev/null || echo "Unreleased")
    echo "## ${_release_tag} ($(date '+%Y-%m-%d'))"
    echo ""
    generate_fallback_changelog "${commits_data}"
}

main() {
    local _changelog_title="# Changelog"
    local _release_entry
    
    echo "[INFO]: Generating changelog entry..." >&2
    
    # Generate changelog content based on mode
    if [ "${USE_COMMIT_ANALYSIS}" == "true" ]; then
        _release_entry=$(generate_commit_changelog)
    else
        echo "[INFO]: Using PR-based changelog generation (legacy mode)" >&2
        _release_entry=$(generate_pr_changelog)
    fi
    
    echo "[INFO]: Updating changelog file..." >&2
    
    # Update CHANGELOG.md
    if ! grep -q "^${_changelog_title}" "${CHANGELOG_FILE_PATH}"; then
        echo -e "${_changelog_title}\n\n" > "${CHANGELOG_FILE_PATH}"
    fi

    local _tail_changelog
    _tail_changelog=$(tail -n +3 "${CHANGELOG_FILE_PATH}")
    echo -e "${_changelog_title}\n\n${_release_entry}\n\n${_tail_changelog}" > "${CHANGELOG_FILE_PATH}"
    echo "[OK]: Updated changelog"

    echo "[INFO]: Updating release notes..." >&2
    
    # Update release notes
    local _release_notes_header="---\ntitle: Release Notes\nhide:\n  - navigation\n---\n\n# 📌 Release Notes"
    if ! grep -q "^# 📌 Release Notes" "${RELEASE_NOTES_FILE_PATH}"; then
        echo -e "${_release_notes_header}\n\n" > "${RELEASE_NOTES_FILE_PATH}"
    fi

    local _tail_notes
    _tail_notes=$(tail -n +9 "${RELEASE_NOTES_FILE_PATH}")
    echo -e "${_release_notes_header}\n\n${_release_entry}\n\n${_tail_notes}" > "${RELEASE_NOTES_FILE_PATH}"
    echo "[OK]: Updated release notes"

    # Commit and push if requested
    if [ "${_IS_COMMIT}" == true ]; then
        local _release_tag
        _release_tag=$(gh release view --json tagName -q ".tagName" 2>/dev/null || echo "latest")
        echo "[INFO]: Committing changelog version '${_release_tag}'..." >&2
        git add "${CHANGELOG_FILE_PATH}" || exit 2
        git add "${RELEASE_NOTES_FILE_PATH}" || exit 2
        git commit -m "docs: update changelog version '${_release_tag}'" || exit 2
        echo "[OK]: Committed changes"

        if [ "${_IS_PUSH}" == true ]; then
            echo "[INFO]: Pushing changes..." >&2
            git push || exit 2
            echo "[OK]: Pushed changes"
        fi
    fi
}

main
## --- Main --- ##
