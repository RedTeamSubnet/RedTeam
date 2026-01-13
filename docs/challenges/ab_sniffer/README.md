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

## Submission

For general instructions on how to build and push your submission, please refer to the [Building a Submission Commit](../../guides/building-commit.md) guide.

## 📑 References

- Docker - <https://docs.docker.com>
