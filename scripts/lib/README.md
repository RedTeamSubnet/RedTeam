# Enhanced Changelog Automation

This directory contains the enhanced changelog automation system that supports both traditional PR-based changelog generation and AI-powered commit analysis.

## Files

- **`changelog.sh`**: Main script with enhanced functionality
- **`lib/git-utils.sh`**: Git operations utilities
- **`lib/commit-collector.sh`**: Collect commits from main repo and submodules
- **`lib/gemini-client.sh`**: Gemini API integration for AI-generated changelogs

## Features

### 🔄 Dual Mode Operation
- **Commit Analysis Mode** (default): Uses LLM to analyze commits and generate intelligent changelogs
- **Legacy PR Mode**: Traditional GitHub PR-based changelog generation

### 🎯 Commit Analysis Features
- Collects commits since last release from main repository
- Recursively processes all submodule commits
- Groups commits by type (features, fixes, improvements, etc.)
- Acknowledges contributors
- Falls back gracefully when API is unavailable

### 🤖 AI Integration
- Uses Google Gemini API for intelligent changelog generation
- Understands commit patterns and generates user-friendly descriptions
- Handles rate limiting and errors gracefully
- Provides fallback to simple commit listing

## Usage

### Basic Usage
```bash
# Generate changelog with commit analysis + AI (default)
./scripts/changelog.sh -c -p

# Use traditional PR-only method
./scripts/changelog.sh --use-pr-only -c

# Generate without committing
./scripts/changelog.sh
```

### Environment Variables
- `GEMINI_API_KEY`: Required for AI-powered changelog generation
- `USE_COMMIT_ANALYSIS`: Enable/disable commit analysis (default: true)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-pro)

## GitHub Actions Integration

The enhanced workflow:
1. Fetches full git history and submodules
2. Installs required dependencies (jq, curl)
3. Runs changelog generation with commit analysis
4. Falls back to PR method if API key is missing

### Required Secrets
- `GEMINI_API_KEY`: Your Google Gemini API key
- `GITHUB_TOKEN`: Already provided by GitHub Actions

## Error Handling

The system includes robust error handling:
- Missing API key → Falls back to simple commit listing
- API rate limits → Uses fallback method
- No commits found → Falls back to PR method
- Missing dependencies → Clear error messages

## Backward Compatibility

- Existing workflows continue to work unchanged
- Legacy `--use-pr-only` flag maintains old behavior
- Same output file format and structure
- Graceful degradation when new features aren't available