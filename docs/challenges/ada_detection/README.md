# Anti-Detect Browser Detection (ADA) Challenge

## Overview

The **Anti-Detect Browser Detection (ADA)** challenge tests miners' ability to identify which
**commercial anti-detect browser** is driving a session, while leaving genuine human traffic
untouched.

Each target is a paid desktop application that launches a managed profile and is driven over
its own loopback API. There is no WebDriver or CDP automation flag to key on, so detection
must rely on the product artifacts the anti-detect browser itself leaves behind in the page
environment.

## General Technical Requirements

- **Development Language**: JavaScript (ES6+), one self-contained detector per target
- **Environment**: Docker container environment
- **Architecture**: amd64 (ARM64 at your own risk)
- **State**: Stateless execution with no persistence between runs

## General Guidelines

- **Detection Method**: Analyze product-specific artifacts, patched APIs, injected objects,
  and behavioral patterns.
- **Execution Modes**: Detectors are tested in both headed and headless modes.
- **Human Safety**: A normal headed browser must not trigger a browser or headless detector.
  Any false positive on a human task drives the score to zero.
- **Prohibited Method**: Browser fingerprinting is not allowed.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' detectors.
- 100% similarity = zero score.
- Similarity above 60% will result in rejection of the submission.

## Submission Path

**Dedicated Path:** [`examples/miner_commit/src/commit/`](https://github.com/RedTeamSubnet/ada-detection-challenge/tree/main/examples/miner_commit/src/commit/)

Place your detection module files in this directory before building your commit:

- `ads_power.js`
- `dolphin_anty.js`
- `gologin.js`
- `headless.js`
- `multilogin.js`
- `octo.js`

## Challenge Versions

**Current:**

- [**v3**](./v3.md) - Commercial anti-detect browser identification, independent headless
  classification, and human verification

**Deprecated:**

- [v2](./depricated/v2.md) - NSTBrowser-hardened automation detection with fail-fast scoring
- [v1](./depricated/v1.md)

## Resources & Guides

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) - General submission instructions
- [ADA-3 Testing Manual](./testing_manuals.md) - Local validation and environment guidance
- [Challenge Repository](https://github.com/RedTeamSubnet/ada-detection-challenge/)
- [Miner Repository](https://github.com/RedTeamSubnet/miner/)

## 📑 References

- Docker - <https://docs.docker.com>
