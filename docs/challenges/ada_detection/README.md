# Anti-Detect Automation Detection (AAD) Challenge

## Overview

The **Anti-Detect Automation Detection (AAD)** challenge evaluates a participant`s ability to reliably detect browser automation frameworks operating inside anti-detect browsers, while preserving human safety.

Evaluation runs simulate real-world anti-detect usage where static signals are masked and fingerprints are fresh. Detection must rely on runtime behavior and orchestration patterns.

## Anti-Detect Environment

Each evaluation run involves:

- A **fresh NST-Browser profile**.
- An **isolated Docker container per framework**.
- Masks for browser fingerprints and no shared state between runs.

!!! Info "NST-Browser Dependency"
    Participants need an API key from the [NSTBrowser](https://www.nstbrowser.io/en/pricing) dashboard (Professional plan recommended) for local testing.

## Evaluation Flow

1. **Submission Received**: Detection scripts are submitted via the `/score` endpoint.
2. **Task Generation**: A randomized sequence of multiple automation framework runs and human interactions is generated.
3. **NST-Browser Launch**: A clean instance is started for each task.
4. **Execution**: Automation frameworks connect via WebSocket, while humans interact manually.
5. **Detection Phase**: Scripts may emit detection payloads to `/_payload`.
6. **Scoring**: Results are aggregated and normalized.

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

## Submission

For general instructions on how to build and push your submission, please refer to the [Building a Submission Commit](../../guides/building-commit.md) guide.

## 📑 References

- Docker - <https://docs.docker.com>
