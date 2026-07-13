# Auto Browser Sniffer (AB Sniffer) Challenge

## Overview

The **AB Sniffer** challenge tests miners' ability to detect and correctly identify browser automation frameworks. It evaluates page-local automation signals, framework-specific leaks, headless execution, and false positives in normal human-driven browsers.

Miners must maintain reliable classification across headed and headless execution modes while ensuring that human sessions do not trigger any automation or headless detector.

## General Technical Requirements

- **Development Language**: Node.js SDK development
- **Operating System**: Ubuntu 24.04
- **Environment**: Docker container environment
- **Architecture**: amd64 (ARM64 at your own risk)

## General Guidelines

- **Detection Method**: Analyze automation behavior, unique signatures, or behavioral patterns.
- **Execution Modes**: Detectors are tested in both headed and headless modes.
- **Human Safety**: A normal headed browser must not trigger a framework or headless detector.
- **Prohibited Method**: Browser fingerprinting is not allowed.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' SDKs.
- 100% similarity = zero score.
- Similarity above 60% will result in rejection of the submission.

## Submission Path

**Dedicated Path:** [`examples/miner_commit/src/commit/`](https://github.com/RedTeamSubnet/ab-sniffer/tree/main/examples/miner_commit/src/commit/)

Place your detection module files in this directory before building your commit:

- `nodriver.js`
- `seleniumbase.js`
- `seleniumdriverless.js`
- `patchright.js`
- `puppeteerextra.js`
- `zendriver.js`
- `botasaurus.js`
- `pydoll.js`
- `headless.js`

## Challenge Versions

**Current:**

- [**v6**](./v6.md) - Framework detection, independent headless classification, and human verification

**Deprecated:**

- [v5 (Dec 02, 2025)](./deprecated/v5.md)
- [v4 (Oct 16, 2025)](./deprecated/v4.md)
- [v2 (July 15, 2025)](./deprecated/v2.md)
- [v1 (June 10, 2025)](./deprecated/v1.md)

## Resources & Guides

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) - General submission instructions
- [AB Sniffer v6 Testing Manual](./testing_manuals.md) - Local validation and environment guidance
- [Challenge Repository](https://github.com/RedTeamSubnet/ab-sniffer/)
- [Miner Repository](https://github.com/RedTeamSubnet/miner/)

## 📑 References

- Docker - <https://docs.docker.com>
