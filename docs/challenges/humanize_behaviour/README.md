# Humanize Behaviour Challenge

## Overview

The **Humanize Behaviour** challenge tests bot scripts' ability to mimic human interaction with a web UI form. It evaluates how well a bot navigates UI elements, interacts with form fields, and submits data without being caught by detection systems that analyze mouse movement, keyboard interaction, and behavioral patterns.

Miners must demonstrate precise, human-like interactions that vary naturally between sessions to avoid detection.

## General Technical Requirements

- **Language**: Python 3.10
- **Operating System**: Ubuntu 24.04
- **Environment**: Docker container (`selenium/standalone-chrome:4.28.1`)
- **Architecture**: amd64 (ARM64 at your own risk)

## General Guidelines

- **Driver Usage**: Use the provided Selenium driver to ensure proper evaluation.
- **Execution Modes**: Bot scripts must run on a **headless browser**.
- **Dependency Limitation**: Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted.
- **Script Limitation**: Your script must not exceed 2,000 lines. Larger scripts will be considered invalid.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' scripts.
- 100% similarity = zero score.
- Similarity above 60% results in rejection of the submission.

## Submission Path

**Dedicated Path:** [examples/humanize_behaviour_v5/src/bot/](https://github.com/RedTeamSubnet/miner/tree/main/examples/humanize_behaviour_v5/src/bot/)

Place your bot script in this directory before building your commit:

- `bot.py` - Your main bot implementation

Ensure your bot script follows the template structure and keeps the `run_bot()` function signature unchanged.

## Challenge Versions

**Current:**

- [**v5** (Active after Sep 04, 2025 10:00 UTC)](./v5.md) - Dynamic movements with human-in-the-loop & bezier curve detection

**Deprecated:**

- [v3 (April 11, 2025)](./depricated/v3.md)
- [v2 (March 18, 2025)](./depricated/v2.md)
- [v1 (Feb 12, 2025)](./depricated/v1.md)

## Resources & Guides

- [Testing Manual](./testing_manuals.md) - Local testing guidelines for bot scripts
- [Building a Submission Commit](../../guides/building-commit.md) - General submission instructions

## 📑 References

- Docker - <https://docs.docker.com>
