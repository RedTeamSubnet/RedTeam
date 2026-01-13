---
title: Device Fingerprinter v1
---
# Device Fingerprinter v1 (Active after September [20]th 2025 10:00 UTC)

![thumnail](../../assets/images/challenges/dev_fingerprinter_v1/thumbnail.png)

## Overview

**Device Fingerprinter v1** tests miners' ability to develop a browser SDK that can accurately detect the driver type used by bots interacting with a webpage.

For general challenge information, technical requirements, and plagiarism policies, please refer to the [Device Fingerprinter README](../README.md).

---

## Example Code

Example codes for the Device Fingerprinter v1 can be found in the [`redteam_core/miner/commits/dev_fingerprinter_v1/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/dev_fingerprinter_v1/) directory.

### Core Requirements

1. Use our template from [`redteam_core/miner/commits/dev_fingerprinter_v1/src/fingerprinter/fingerprinter.js`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/dev_fingerprinter_v1/src/fingerprinter/fingerprinter.js)
2. Keep the `runFingerprinting()` function signature and export unchanged
3. Your fingerprinter must:
   - Collect device and browser fingerprint data
   - Generate a unique fingerprint hash
   - Send results to the designated endpoint
   - Complete without errors

### Key Guidelines

- **Detection Accuracy**: Your fingerprinter must accurately identify different devices and provide consistent hash values for the same device across multiple runs.
- **Fingerprint Collection**: Analyze properties and signatures to uniquely identify iOS devices.
- **API Integration**: Handle errors gracefully when sending formatted JSON payloads.

## Submission Guide

To build and submit your solution, please follow the [Building a Submission Commit](../../../guides/building-commit.md) guide.
