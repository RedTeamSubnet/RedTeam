---
title: Challenges
---

# ❓ Challenges

## Overview

The RedTeam Challenge Menu provides access to various challenges designed to test and evaluate miners' technical capabilities across different security and automation domains.

Each challenge focuses on a specific problem space, with multiple versions released over time to increase difficulty and adapt to evolving techniques and requirements.

## Challenge Versions & History

Each challenge maintains version history in its documentation:

- **Active Versions**: Current challenges accepting submissions (see each challenge's README)
- **Deprecated Versions**: Previous challenge iterations stored in `deprecated/` folders for historical reference
- **Inactive Challenges**: Challenges that are no longer accepting submissions (marked in the navigation below)

!!! warning "Important"
    - Do not develop submissions for deprecated challenge versions
    - Avoid making submissions for inactive challenges - they will be rejected
    - Always check the challenge README for the current active version

## Testing & Validation

Each challenge provides testing resources to help you validate submissions locally before building and submitting:

- **Testing Manuals**: Step-by-step guides for local testing (see individual challenge READMEs)
- **Validation Tools**: Pre-submission checks (e.g., ESLint for AB Sniffer)
- **Example Code**: Templates and reference implementations in challenge repositories

We strongly recommend testing your submission locally to ensure it meets all requirements before final submission.

## Miner Checklist

Follow these steps to successfully submit your challenge solution:

- [X] **Get Active Challenge**
- Review the active challenge version from the challenge's README
- Read the version-specific documentation for requirements and guidelines
- See [Available Challenges](#available-challenges) below

- [X] **Develop Submission and Test**
- Implement your solution following the provided templates
- Test locally using the testing guides and validation tools
- Ensure your code meets all technical constraints and limitations
- Reference [Testing & Validation](#testing-validation) resources above

- [X] **Put Submission to Dedicated Path**
- Place your submission files in the challenge's dedicated submission path (see each challenge README)
- Verify all required files are included with correct naming

- [X] **Build Commit**
- Follow the [Building a Submission Commit](../miner/workflow/3.build-and-publish.md) guide
- Build and tag your Docker image
- Push the image to your Docker Hub repository

- [X] **Submit the Submission**
- Retrieve the SHA256 digest of your pushed image
- Update your miner's `active_commit.yaml` with the image reference
- Submit and monitor your score

## Available Challenges

- **[Auto Browser Sniffer (AB Sniffer)](ab_sniffer/README.md)** Detect and identify automation frameworks by analyzing behavior and technical signatures.
- **[Humanize Behaviour](humanize_behaviour/README.md)** Develop bot scripts that mimic natural human interaction with web forms.
- **[Anti-Detect Automation Detection (AAD)](ada_detection/README.md)** Detect browser automation inside anti-detect environments where fingerprints are masked.
- **[Device Fingerprinter](dev_fingerprinter/README.md) Inactive** Create browser SDKs that accurately fingerprint and identify devices.
