# Device Fingerprinter Challenge

## Overview

The **Device Fingerprinter** challenge tests miners' ability to develop a browser SDK that can accurately detect the driver type used by bots interacting with a webpage. Miners must create a JavaScript fingerprinter that distinguishes between different devices using browser properties, behavior patterns, and technical signatures.

## General Technical Requirements

- **Language**: JavaScript (ES6+)
- **Operating System**: Ubuntu 24.04
- **Architecture**: amd64
- **Environment**: Docker container support

## General Guidelines

- **Fingerprint Collection**: Collect comprehensive browser and device properties while analyzing WebDriver signatures and automation artifacts.
- **Data Processing**: Generate unique, consistent fingerprint hashes and follow the provided API endpoint structure for JSON payloads.
- **Dependency Limitation**: Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted.
- **Script Limitation**: Your script must not exceed 2,000 lines. Larger scripts will be considered invalid.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' scripts.
- 100% similarity = zero score.
- Similarity above 60% results in proportional score penalties based on the **detected similarity percentage**.

## Submission Path

**Dedicated Path:** `examples/dev_fingerprinter_v1/src/fingerprinter/`

Place your fingerprinting script in this directory before building your commit:
- `fingerprinter.js` - Your main fingerprinting implementation

Ensure your script keeps the `runFingerprinting()` function signature and export unchanged.

## Submission

For general instructions on how to build and push your submission, please refer to the [Building a Submission Commit](../../miner/building-commit.md) guide.

## 📑 References

- Docker - <https://docs.docker.com>
