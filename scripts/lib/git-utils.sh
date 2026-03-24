#!/usr/bin/env bash
# Git utility functions for changelog generation

# Get commits since last tag/release
get_commits_since_last_release() {
    local repo_path="${1:-.}"
    local format="${2:-%H|%an|%ae|%ad|%s}"
    
    cd "${repo_path}" || return 1
    
    # Get latest tag
    local latest_tag
    latest_tag=$(git describe --tags --abbrev=0 2>/dev/null) || {
        echo "[WARN]: No previous tags found, using all commits" >&2
        git log --pretty=format:"${format}" --date=short
        return 0
    }
    
    # Get commits since latest tag
    git log "${latest_tag}..HEAD" --pretty=format:"${format}" --date=short
}

# Get submodule information
get_submodules() {
    git submodule status | awk '{print $2}' 2>/dev/null || true
}

# Get commits from a specific submodule since its last update
get_submodule_commits() {
    local submodule_path="${1}"
    local format="${2:-%H|%an|%ae|%ad|%s}"
    
    if [ ! -d "${submodule_path}" ]; then
        echo "[WARN]: Submodule path '${submodule_path}' not found" >&2
        return 1
    fi
    
    cd "${submodule_path}" || return 1
    
    # Get commits from last 30 days or since last tag
    local latest_tag
    latest_tag=$(git describe --tags --abbrev=0 2>/dev/null)
    
    if [ -n "${latest_tag}" ]; then
        git log "${latest_tag}..HEAD" --pretty=format:"${format}" --date=short 2>/dev/null || true
    else
        git log --since="30 days ago" --pretty=format:"${format}" --date=short 2>/dev/null || true
    fi
}

# Validate git repository
validate_git_repo() {
    local repo_path="${1:-.}"
    if ! git -C "${repo_path}" rev-parse --git-dir >/dev/null 2>&1; then
        echo "[ERROR]: Not a git repository: ${repo_path}" >&2
        return 1
    fi
    return 0
}