#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


if ! command -v git >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'git' command, please install it first!" >&2
	exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'gh' command, please install it first!" >&2
	exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
	echo "[ERROR]: You need to login: 'gh auth login'!" >&2
	exit 1
fi

if [ ! -f ./scripts/get-version.sh ]; then
	echo "[ERROR]: 'get-version.sh' script not found!" >&2
	exit 1
fi

# shellcheck disable=SC1091
[ -f .env ] && . .env

# Check for enhanced changelog capabilities
USE_COMMIT_ANALYSIS="${USE_COMMIT_ANALYSIS:-true}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

# Source utility libraries for commit analysis if available
if [ "${USE_COMMIT_ANALYSIS}" == "true" ] && [ -f "${_SCRIPT_DIR}/lib/commit-collector.sh" ]; then
    # Check for required tools
    if command -v jq >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
        # shellcheck source=./lib/commit-collector.sh
        source "${_SCRIPT_DIR}/lib/commit-collector.sh"
        # shellcheck source=./lib/gemini-client.sh  
        source "${_SCRIPT_DIR}/lib/gemini-client.sh"
    else
        echo "[WARN]: Missing jq/curl, disabling commit analysis for release notes" >&2
        USE_COMMIT_ANALYSIS=false
    fi
fi
## --- Base --- ##


## --- Variables --- ##
# Flags:
_IS_BUILD=false
_USE_COMMIT_ANALYSIS="${USE_COMMIT_ANALYSIS}"
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -b, --build           Enable build step. Default: false
    --use-commit-notes    Use commit analysis for release notes (default)
    --use-simple-notes    Use GitHub's auto-generated release notes
    -h, --help            Show this help message.

ENVIRONMENT:
    GEMINI_API_KEY        Optional: For AI-generated release notes
    USE_COMMIT_ANALYSIS   Enable/disable commit analysis (default: true)

EXAMPLES:
    ${0} -b                      # Build and create release with commit analysis
    ${0} --use-simple-notes      # Use GitHub's auto-generated notes
    ${0} --build                 # Same as -b
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-b | --build)
			_IS_BUILD=true
			shift;;
		--use-commit-notes)
			_USE_COMMIT_ANALYSIS=true
			shift;;
		--use-simple-notes)
			_USE_COMMIT_ANALYSIS=false
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


if [ "${_IS_BUILD}" == true ]; then
	if [ ! -f ./scripts/build.sh ]; then
		echo "[ERROR]: 'build.sh' script not found!" >&2
		exit 1
	fi

	./scripts/build.sh -c || exit 2
fi


## --- Release Notes Generation --- ##

# Generate release notes using commit analysis (similar to changelog)
generate_commit_release_notes() {
    echo "[INFO]: Generating release notes from commit analysis..." >&2
    
    local commits_data
    commits_data=$(collect_commit_data "${_PROJECT_DIR}")
    
    if [ -z "${commits_data}" ]; then
        echo "[WARN]: No commits found for release notes" >&2
        return 1
    fi
    
    get_commit_stats "${commits_data}"
    
    # Try to generate release notes with Gemini
    if [ -n "${GEMINI_API_KEY}" ]; then
        echo "[INFO]: Generating AI-powered release notes..." >&2
        local ai_notes
        if ai_notes=$(generate_changelog_with_gemini "${commits_data}"); then
            echo "${ai_notes}"
            return 0
        else
            echo "[WARN]: AI generation failed, using fallback method" >&2
        fi
    else
        echo "[INFO]: GEMINI_API_KEY not set, using fallback method" >&2
    fi
    
    # Fallback to simple commit list
    echo "[INFO]: Generating simple release notes from commits..." >&2
    generate_fallback_changelog "${commits_data}"
}

# Generate simple release notes (GitHub auto-generated)
generate_simple_release_notes() {
    echo "[INFO]: Using GitHub's auto-generated release notes" >&2
    return 0  # Return success, GitHub will handle generation
}

## --- Release Notes Generation --- ##


## --- Main --- ##
main()
{
	local _current_version
	_current_version="$(./scripts/get-version.sh)"
	echo "[INFO]: Creating release for version: 'v${_current_version}'..."
	
	# Generate release notes based on method choice
	if [ "${_USE_COMMIT_ANALYSIS}" == "true" ]; then
		local release_notes
		if release_notes=$(generate_commit_release_notes); then
			echo "[INFO]: Creating release with enhanced release notes..." >&2
			# Create release with custom notes
			echo "${release_notes}" | gh release create "v${_current_version}" ./dist/* --notes-file -
		else
			echo "[WARN]: Commit analysis failed, falling back to auto-generated notes" >&2
			gh release create "v${_current_version}" ./dist/* --generate-notes
		fi
	else
		generate_simple_release_notes
		gh release create "v${_current_version}" ./dist/* --generate-notes
	fi
	
	echo "[OK]: Release 'v${_current_version}' created successfully."
}

main
## --- Main --- ##
