#!/usr/bin/env bash
# Gemini API client for changelog generation

# Filter out automated commits (github-actions, bots, etc.)
filter_automated_commits() {
    local commits_data="${1}"

    # Skip commits from automated accounts
    echo "${commits_data}" | grep -v -E "(github-actions@|dependabot\[bot\]|renovate\[bot\]|bot@|action@)"
}

# Generate changelog using Gemini API
generate_changelog_with_gemini() {
    local commits_data="${1}"
    local api_key="${GEMINI_API_KEY}"
    local model="${GEMINI_MODEL:-gemini-pro}"

    if [ -z "${api_key}" ]; then
        echo "[ERROR]: GEMINI_API_KEY not set" >&2
        return 1
    fi

    if [ -z "${commits_data}" ]; then
        echo "[ERROR]: No commit data provided" >&2
        return 1
    fi

    # Filter out automated commits
    local filtered_commits
    filtered_commits=$(filter_automated_commits "${commits_data}")

    if [ -z "${filtered_commits}" ]; then
        echo "[WARN]: No user commits found after filtering automated commits" >&2
        return 1
    fi

    # Create improved prompt for Gemini
    local prompt
    prompt=$(cat <<EOF
Generate a changelog from these commits. Output ONLY the markdown sections, no intro text.

Format: hash|author|email|date|message

COMMITS:
${filtered_commits}

Rules:
1. Group into: ## Features, ## Improvements, ## Bug Fixes, ## Other Changes
2. Skip empty sections
3. One line per change: "- Description (@author)". But be careful to this case where username includes space you need to skip `@` symbol and use only username.
4. NO intro phrases like "Here's a changelog" or explanations
EOF
)

    # Prepare API request
    local api_url="https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${api_key}"
    local json_payload
    json_payload=$(jq -n --arg prompt "${prompt}" '{
        contents: [{
            parts: [{
                text: $prompt
            }]
        }]
    }')

    # Make API request
    local response
    response=$(curl -s -X POST "${api_url}" \
        -H "Content-Type: application/json" \
        -d "${json_payload}")

    # Check for API errors
    if echo "${response}" | jq -e '.error' >/dev/null 2>&1; then
        local error_message
        error_message=$(echo "${response}" | jq -r '.error.message // "Unknown API error"')
        echo "[ERROR]: Gemini API error: ${error_message}" >&2
        return 1
    fi

    # Extract generated text
    echo "${response}" | jq -r '.candidates[0].content.parts[0].text // empty' 2>/dev/null || {
        echo "[ERROR]: Failed to parse Gemini response" >&2
        return 1
    }
}

# Fallback changelog generation (simple format)
generate_fallback_changelog() {
    local commits_data="${1}"

    # Filter out automated commits
    local filtered_commits
    filtered_commits=$(filter_automated_commits "${commits_data}")

    if [ -z "${filtered_commits}" ]; then
        echo "## Changes"
        echo ""
        echo "- No user commits found (only automated commits detected)"
        echo ""
        return 0
    fi

    echo "## Changes"
    echo ""

    # Process commit data and create simple changelog
    echo "${filtered_commits}" | while IFS='|' read -r hash author email date message; do
        [ -z "${hash}" ] && continue
        # Clean up commit message (remove conventional commit prefixes)
        clean_message=$(echo "${message}" | sed -E 's/^(feat|fix|docs|style|refactor|test|chore)(\([^)]+\))?: //')
        echo "- ${clean_message} (@${author})"
    done

    echo ""
}
