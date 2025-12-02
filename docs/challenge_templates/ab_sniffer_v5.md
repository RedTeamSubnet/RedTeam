---
title: Auto Browser Sniffer v5
---
# AB Sniffer v5 Submission Guide (Active after 2025 December 02 10:00 UTC )

## Overview

**AB Sniffer v5** refines the challenge by introducing a new modular architecture. This version requires participants to build individual detection modules for each target framework. The challenge evaluates how well the SDK can analyze automation behavior and identify unique characteristics or "leaks" from different automation tools interacting with a web page, as well as human-in-the-loop interaction.

Participants must demonstrate precise detection capabilities across multiple automation frameworks while maintaining reliability across different execution modes and human-in-the-loop scenarios.

---

## Example Code and Submission Instructions

Example codes for AB Sniffer v5 can be found in the [`redteam_core/miner/commits/ab_sniffer_v5/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/ab_sniffer_v5/) directory.

### Technical Requirements

- Node.js SDK development
- Ubuntu 24.04
- Docker container environment
- **Development Environment**: Participants are required to develop their solutions in a separate GitHub repository.

### Mandatory Requirements

1. Use the templates provided in the [`redteam_core/miner/commits/ab_sniffer_v5/src/detections/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/ab_sniffer_v5/src/detections/) directory for each framework.
2. Implement the detection logic within the individual files found in the `src/detections/` directory. **Do not** change the function names (e.g., `detect_nodriver`, `detect_botasaurus`).
3. Your detection functions must:
   - Return a **boolean** value: `true` if the specific framework for that file is detected, and `false` otherwise.
   - Be self-contained. Each file is responsible for detecting only its corresponding framework.
   *Note*: Be mindful that human interaction can sometimes trigger signals similar to automation frameworks. A robust solution must be able to distinguish human behavior cleanly to avoid collisions.

### Target Frameworks

Your SDK should be capable of detecting these automation frameworks and scenarios:

- **nodriver**
- **seleniumbase**
- **selenium-driverless**
- **patchright**
- **puppeteerextra**
- **zendriver**
- **botasaurus**
- **pydoll**

### Key Guidelines

- **Detection Method**: Analyze automation behavior, unique signatures, or behavioral patterns.
- **Output Format**: Each detection script must return a simple boolean (`true` or `false`).
- **Execution Modes**: SDK will be tested in both headless and headfull modes.
- **Reliability**: Each of the 9 targets (8 frameworks + 1 human) will be tested across three separate sessions, for a total of 27 evaluation sessions.
- **Technical Setup**:
    - Enable headless mode
    - Use amd64 architecture (ARM64 at your own risk)
- **Limitations**
    - Your script must not exceed 500 lines. If it does, it will be considered invalid, and you will receive a score of zero.
    - **Prohibited Methods:** Solutions relying on browser fingerprinting are strictly forbidden. Any such solution detected will result in immediate disqualification and will get a score of zero.

### Evaluation Criteria

- **Detection Accuracy**: Correctly identifying automation frameworks by name.
- **Consistency**: Maintaining accuracy across multiple test runs.
- **Coverage**: Number of frameworks successfully detected.
- **Minimum Requirement**: Must detect at least 4 frameworks, **including human**, with 100% accuracy to qualify.
- **Human Detection Penalty**: Failure to detect human interaction will result in an automatic score of zero for the entire submission.

### Scoring System

The final score is calculated based on performance across all 27 evaluation sessions (9 targets x 3 sessions each).

- **Session Scoring Rules**:
    - **1 point** for a "Perfect Detection."
    - **0.1 points** for a "Collision."
    - **0 points** for a "Failed Detection."

- **Final Score Calculation**:
    - `Final Score = (Sum of all 27 session scores) / 27`

- **Example Scenario**:
    - **4 automation frameworks** are detected perfectly across all three sessions, contributing `4 × 3 × 1.0 = 12.0` points.
    - **Human interaction** is detected perfectly across all three sessions, contributing `1 × 3 × 1.0 = 3.0` points.
    - **2 frameworks** are detected with collisions across all three sessions, contributing `2 × 3 × 0.1 = 0.6` points.
    - **2 frameworks** are missed across all three sessions, contributing `2 × 3 × 0.0 = 0.0` points.
    - **Total Accumulated Points**: `12.0 + 3.0 + 0.6 + 0.0 = 15.6` points.
    - **Final Score**: The score is calculated as `15.6 / 27 ≈ 0.5777`.
    - ***Note on Human Collisions***: *The score above is only valid if no collision with 'human' occurred. If any session involves a collision with 'human', the **Final Score for the entire submission is 0**.*

### Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other participants' submissions.
- 100% similarity = zero score.
- Similarity above 60% will result in proportional score penalties based on the **detected similarity percentage**.

### Pre-Submission Check

Before submitting, you **must** ensure your code passes our ESLint configuration. You can do this by using our provided playground environment on Replit [https://replit.com/@redteamsn61/absnifferv1eslintcheck#README.md]. Submissions that do not pass the linting check will be rejected.

## Submission Guide

Follow 1~6 steps to submit your SDK.

1. **Navigate to the AB Sniffer v5 Commit Directory**

    ```bash
    cd redteam_core/miner/commits/ab_sniffer_v5
    ```

2. **Build the Docker Image**

    To build the Docker image for the AB Sniffer v5 submission, run:

    ```bash
    docker build -t my_hub/ab_sniffer_v5-miner:0.0.1 .

    # For MacOS (Apple Silicon) to build AMD64:
    DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/ab_sniffer_v5-miner:0.0.1 .
    ```

3. **Log in to Docker**

    Log in to your Docker Hub account using the following command:

    ```bash
    docker login
    ```

    Enter your Docker Hub credentials when prompted.

4. **Push the Docker Image**

    Push the tagged image to your Docker Hub repository:

    ```bash
    docker push myhub/ab_sniffer_v5:0.0.1
    ```

5. **Retrieve the SHA256 Digest**

    After pushing the image, retrieve the digest by running:

    ```bash
    docker inspect --format='{{index .RepoDigests 0}}' myhub/ab_sniffer_v5:0.0.1
    ```

6. **Update active_commit.yaml**

    Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

    ```yaml
    - ab_sniffer_v5---myhub/ab_sniffer_v5@<sha256:digest>
    ```

---

## 📑 References

- Docker - <https://docs.docker.com>
