#!/usr/bin/env bash
# Commit data collection for main repo and submodules

# Source git utilities
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=./git-utils.sh
source "${SCRIPT_DIR}/git-utils.sh"

# Collect all commit data
collect_commit_data() {
    local project_dir="${1:-..}"
    cd "${project_dir}" || return 1
    
    echo "[INFO]: Collecting commits from main repository..." >&2
    
    # Validate main repo
    if ! validate_git_repo "."; then
        return 1
    fi
    
    # Collect main repo commits
    local main_commits
    main_commits=$(get_commits_since_last_release ".")
    
    echo "[INFO]: Collecting commits from submodules..." >&2
    
    # Collect submodule commits
    local submodule_commits=""
    local submodules
    submodules=$(get_submodules)
    
    if [ -n "${submodules}" ]; then
        while IFS= read -r submodule; do
            [ -z "${submodule}" ] && continue
            echo "[INFO]: Processing submodule: ${submodule}" >&2
            
            local sub_commits
            sub_commits=$(get_submodule_commits "${submodule}")
            
            if [ -n "${sub_commits}" ]; then
                # Add submodule prefix to commits
                echo "${sub_commits}" | while IFS='|' read -r hash author email date message; do
                    [ -z "${hash}" ] && continue
                    echo "${hash}|${author}|${email}|${date}|[${submodule}] ${message}"
                done
                submodule_commits="${submodule_commits}${sub_commits}"$'\n'
            fi
        done <<< "${submodules}"
    else
        echo "[INFO]: No submodules found" >&2
    fi
    
    # Combine all commits
    {
        echo "${main_commits}"
        echo "${submodule_commits}"
    } | grep -v '^$' | sort -t'|' -k4 -r  # Sort by date (newest first)
}

# Get commit statistics with filtering info
get_commit_stats() {
    local commits_data="${1}"
    
    local total_commits
    total_commits=$(echo "${commits_data}" | grep -c '|' || echo "0")
    
    local unique_authors
    unique_authors=$(echo "${commits_data}" | cut -d'|' -f2 | sort -u | grep -c '.' || echo "0")
    
    # Count automated commits
    local automated_commits
    automated_commits=$(echo "${commits_data}" | grep -cE "(github-actions@|dependabot\[bot\]|renovate\[bot\]|bot@|action@)" || echo "0")
    
    local user_commits=$((total_commits - automated_commits))
    
    echo "[INFO]: Found ${total_commits} commits from ${unique_authors} authors" >&2
    
    if [ "${automated_commits}" -gt 0 ]; then
        echo "[INFO]: Filtering out ${automated_commits} automated commits, ${user_commits} user commits remaining" >&2
    fi
}