# Device Fingerprinter Challenge

## Overview

The Device Fingerprinter challenge tests miners' ability to develop a browser SDK that can accurately and consistently identify physical
devices across multiple browser environments. Miners must create a JavaScript fingerprinter that generates a unique, persistent ID for a
specific device, regardless of whether it is accessed via Chrome, Safari, or Brave.

## General Technical Requirements

- **Language**: JavaScript (ES6+)
- **Operating System**: Ubuntu 24.04
- **Architecture**: amd64
- **Environment**: Docker container support

## General Guidelines

- **Fingerprint Collection**: Collect browser and device properties to identify the physical hardware across different browser engines.
- **Data Processing**: Generate unique, consistent fingerprint hashes and follow the provided API endpoint structure for JSON payloads.
- **Dependency Limitation**: Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted.
- **Script Limitation**: Your script must not exceed 2,000 lines. Larger scripts will be considered invalid.

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' scripts.
- Under 40% Similarity: No penalty is applied.
- 40% to 60% Similarity: Results in proportional score penalties based on the detected similarity percentage.
- Above 60% Similarity: Results in an automatic score of zero (Disqualification).

## Submission

For general instructions on how to build and push your submission, please refer to the [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) guide.

## 📑 References

- Docker - <https://docs.docker.com>
