# Enhanced Changelog & Release Automation

This directory contains the enhanced automation system that supports both traditional PR-based generation and AI-powered commit analysis for both changelog and release notes.

## Files

- **`changelog.sh`**: Main changelog script with enhanced functionality
- **`release.sh`**: Enhanced release script using same commit analysis
- **`lib/git-utils.sh`**: Git operations utilities
- **`lib/commit-collector.sh`**: Collect commits from main repo and submodules
- **`lib/gemini-client.sh`**: Gemini API integration for AI-generated content

## Features

### 🔄 Dual Mode Operation
- **Commit Analysis Mode** (default): Uses LLM to analyze commits and generate intelligent content
- **Legacy PR/Auto Mode**: Traditional GitHub PR-based changelog / auto-generated release notes

### 🎯 Commit Analysis Features
- Collects commits since last release from main repository
- Recursively processes all submodule commits
- Groups commits by type (features, fixes, improvements, etc.)
- Acknowledges contributors
- Falls back gracefully when API is unavailable

### 🤖 AI Integration
- Uses Google Gemini API for intelligent content generation
- Understands commit patterns and generates user-friendly descriptions
- Handles rate limiting and errors gracefully
- Provides fallback to simple commit listing

## Usage

### Changelog Generation
```bash
# Generate changelog with commit analysis + AI (default)
./scripts/changelog.sh -c -p

# Use traditional PR-only method
./scripts/changelog.sh --use-pr-only -c

# Generate without committing
./scripts/changelog.sh
```

### Release Creation
```bash
# Create release with enhanced commit-based notes (default)
./scripts/release.sh -b

# Use GitHub's auto-generated release notes
./scripts/release.sh --use-simple-notes -b

# Create release without building
./scripts/release.sh
```

### Environment Variables
- `GEMINI_API_KEY`: Required for AI-powered content generation
- `USE_COMMIT_ANALYSIS`: Enable/disable commit analysis (default: true)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-pro)

## Integration

### Changelog Workflow
The enhanced workflow:
1. Fetches full git history and submodules
2. Installs required dependencies (jq, curl)
3. Runs changelog generation with commit analysis
4. Falls back to PR method if API key is missing

### Release Workflow  
The enhanced release process:
1. Collects commits using same logic as changelog
2. Generates AI-powered release notes (if API key available)
3. Creates GitHub release with custom notes
4. Falls back to GitHub auto-generation if needed

### Required Secrets
- `GEMINI_API_KEY`: Your Google Gemini API key
- `GITHUB_TOKEN`: Already provided by GitHub Actions

## Consistency Features

### 📋 **Matching Content**
Both `changelog.sh` and `release.sh` now use:
- ✅ **Same commit collection** logic
- ✅ **Same filtering** (removes github-actions, bots)  
- ✅ **Same AI prompting** and formatting
- ✅ **Same fallback** mechanisms
- ✅ **Same contributor** attribution (@username)

### 🔄 **Synchronized Output**
- Changelog entries match release notes format
- Both use identical commit analysis  
- Consistent categorization (Features, Improvements, Bug Fixes)
- Same author acknowledgment style

## Error Handling

The system includes robust error handling:
- Missing API key → Falls back to simple commit listing / GitHub auto-generation
- API rate limits → Uses fallback method
- No commits found → Falls back to PR method / GitHub auto-generation
- Missing dependencies → Clear error messages with graceful degradation

## Backward Compatibility

- Existing workflows continue to work unchanged
- Legacy flags maintain old behavior (`--use-pr-only`, `--use-simple-notes`)
- Same output file format and structure
- Graceful degradation when new features aren't available