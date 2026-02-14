# Anti-Detect Automation Detection (AAD) Challenge

## Overview

The **Anti-Detect Automation Detection (AAD)** challenge evaluates a participant's ability to reliably detect browser automation frameworks operating inside anti-detect browsers, while preserving human safety.

Evaluation runs simulate real-world anti-detect usage where static signals are masked and fingerprints are fresh. Detection must rely on runtime behavior and orchestration patterns.

## Anti-Detect Environment

Each evaluation run involves:

- A **fresh NST-Browser profile**.
- An **isolated Docker container per framework**.
- Masks for browser fingerprints and no shared state between runs.

!!! Info "NST-Browser Dependency"
    Participants need an API key from the [NSTBrowser](https://www.nstbrowser.io/en/pricing) dashboard (Professional plan recommended) for local testing.

## Features of ADA Detection v2

- **Hardened NSTBrowser Environment**: Advanced obfuscation including dynamic fingerprinting and hardware simulation (8GB RAM, 16 Cores).
- **Engine-Level Stealth**: `AutomationControlled` flags are disabled at the browser engine level to eliminate static detection signals.
- **Fail-Fast Scoring**: High-stakes evaluation where missing critical targets (Selenium) or exceeding miss limits results in an immediate 0.0 score.
- **Protocol-Level Verification**: Mandatory detection of low-level communication patterns (Webdriver and WebSocket).
- **Selenium Safety Gate**: Mandatory detection of `seleniumbase` and `selenium_driverless` is required for incentive eligibility.
- **Similarity/time decay**: Similarity penalties apply to lookalike submissions; scores decay over 15 days to encourage refreshed heuristics.

## Evaluation Flow

1. **Submission Received**: Detection scripts are submitted via the `/score` endpoint.
2. **Task Generation**: A randomized sequence of multiple automation framework runs and human interactions is generated.
3. **NST-Browser Launch**: A clean instance is started for each task.
4. **Execution**: Automation frameworks connect via WebSocket or WebDriver, while humans interact manually.
5. **Detection Phase**: Scripts may emit detection payloads to `/_payload`.
6. **Scoring**: Results are aggregated and normalized using the Fail-Fast pillars.

## Technical Constraints

- **Language**: JavaScript (ES6+)
- **Environment**: NST-Browser only
- **Architecture**: Docker (amd64 recommended)
- **State**: Stateless execution with no persistence between runs.

## Plagiarism Policy

We maintain strict originality standards:

- All submissions are compared against other participants' SDKs.
- 100% similarity = zero score.
- Similarity above 60% results in proportional score penalties based on the **detected similarity percentage**.

## Submission Path

**Dedicated Path:** [templates/commit/src/detections/](https://github.com/RedTeamSubnet/ada-detection-challenge/tree/main/templates/commit/src/detections/)

Submit your detection scripts as a JSON payload with the following structure:

```json
{
  "detection_files": [
    { "file_name": "nodriver.js", "content": "..." },
    { "file_name": "playwright.js", "content": "..." },
    { "file_name": "patchright.js", "content": "..." },
    { "file_name": "puppeteer.js", "content": "..." },
    { "file_name": "puppeteer_extra.js", "content": "..." },
    { "file_name": "zendriver.js", "content": "..." },
    { "file_name": "selenium_driverless.js", "content": "..." },
    { "file_name": "seleniumbase.js", "content": "..." },
    { "file_name": "webdriver.js", "content": "..." },
    { "file_name": "websocket.js", "content": "..." }
  ]
}
```

Each file must be named exactly as shown and contain self-contained JavaScript (ES6+) detection logic.

## Challenge Versions

- [**v2** (Active after Feb 14, 2026 14:00 UTC)](./v2.md) - Hardened detection with Fail-Fast scoring
- [**v1** (Deprecated)](./depricated/v1.md)

## Resources & Guides

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) - General submission instructions
- [NSTBrowser Official](https://www.nstbrowser.io/en/pricing) - Professional plan required for local testing
- [Challenge Repository](https://github.com/RedTeamSubnet/ada-detection-challenge/)
- [Miner Repository](https://github.com/RedTeamSubnet/miner/)

## 📑 References

- Docker - <https://docs.docker.com>
