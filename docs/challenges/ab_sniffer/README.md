# Auto Browser Sniffer (AB Sniffer) Challenge

## Overview

The **AB Sniffer** challenge tests miners' ability to develop an SDK that can detect and correctly identify automation frameworks by name. The challenge evaluates how well the SDK can analyze automation behavior and identify unique characteristics or "leaks" from different automation tools interacting with a web page.

Miners must demonstrate precise detection capabilities across multiple automation frameworks while maintaining reliability across different execution modes (headless and headfull/headed-but-silent).

## General Technical Requirements

- **Development Language**: Node.js SDK development
- **Operating System**: Ubuntu 24.04
- **Environment**: Docker container environment
- **Architecture**: amd64 (ARM64 at your own risk)

## General Guidelines

- **Detection Method**: Analyze automation behavior, unique signatures, or behavioral patterns.
- **Execution Modes**: The SDK will be tested in both headless and headfull/headed-but-silent modes.
- **Technical Setup**: Headless mode must be enabled.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' SDKs.
- 100% similarity = zero score.
- Similarity above 60% will result in rejection of the submission.

## Submission Path

**Dedicated Path:** [templates/commit/src/detections/](https://github.com/RedTeamSubnet/ab-sniffer-challenge/tree/main/templates/commit/src/detections/)

Place your detection module files in this directory before building your commit:

- `nodriver.js`
- `seleniumbase.js`
- `selenium-driverless.js`
- `patchright.js`
- `puppeteerextra.js`
- `zendriver.js`
- `botasaurus.js`
- `pydoll.js`

## Challenge Versions

**Current:**

- [**v5** (Active after Dec 02, 2025 10:00 UTC)](./v5.md) - Modular detection with human-in-the-loop

**Deprecated:**

- [v4 (Oct 16, 2025)](./depricated/v4.md)
- [v2 (July 15, 2025)](./depricated/v2.md)
- [v1 (June 10, 2025)](./depricated/v1.md)

## Resources & Guides

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) - General submission instructions
- [ESLint Configuration Check](https://replit.com/@redteamsn61/absnifferv1eslintcheck#README.md) - Pre-submission validation on Replit
- [Challenge Repository](https://github.com/RedTeamSubnet/ab-sniffer-challenge/)
- [Miner Repository](https://github.com/RedTeamSubnet/miner/)

## 📑 References

- Docker - <https://docs.docker.com>
