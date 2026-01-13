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

## Submission

For instructions on how to build and push your submission, please refer to the [Building a Submission Commit](../../guides/building-commit.md) guide.

## 📑 References

- Docker - <https://docs.docker.com>
