---
title: Auto Browser Sniffer v4
---
# AB Sniffer v4 Submission Guide (Active after Oct [x]th 2025 14:00 UTC)

## Overview

**AB Sniffer v4** is the next iteration of **Auto Browser Sniffer** challenge which tests participants' ability to develop a SDK that can detect and correctly identify automation frameworks by name. The challenge evaluates how well the SDK can analyze automation behavior and identify unique characteristics or "leaks" from different automation tools interacting with a web page. With the new iteration, we are introducing one more frameworks to be detected which are **Botasaurus**, **Pydoll** and a **human-in-the-loop** interaction scenario.

Participants must demonstrate precise detection capabilities across multiple automation frameworks while maintaining reliability across different execution headless mode and human-in-the-loop scenarios.

---

## Example Code and Submission Instructions

Example codes for the AB Sniffer v4 can be found in the [`redteam_core/miner/commits/ab_sniffer_v4/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/ab_sniffer_v4/) directory.

### Technical Requirements

- Node.js SDK development
- Ubuntu 24.04
- Docker container environment

### Core Requirements

1. Use our template from [`redteam_core/miner/commits/ab_sniffer_v4/src/detection/detection.js`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/ab_sniffer_v4/src/detection/detection.js)
2. Keep the detection function signature unchanged
3. Your SDK must:
   - Detect automation frameworks interacting with the page
   - Output the exact name of the detected tool
   - Work reliably across multiple execution modes

### Target Frameworks

Your SDK should be capable of detecting these automation frameworks:

- **nodriver**
- **selenium**  
- **seleniumbase**
- **patchright**
- **puppeteerextra**
- **zendriver**
- **camoufox**
- **botasaurus**
- **pydoll**
- **human**

### Key Guidelines

- **Detection Method**: Analyze automation behavior, unique signatures, or behavioral patterns
- **Output Format**: Return structured responses with tool name
- **Execution Modes**: SDK will be tested in both headless and headed-but-silent modes
- **Reliability**: Each framework will be tested multiple times randomly to ensure consistent detection
- **Technical Setup**:
    - Enable headless mode
    - Use amd64 architecture (ARM64 at your own risk)
- **Limitations**
    - Your script must not exceed 1,000 lines. If it does, it will be considered invalid, and you will receive a score of zero.
    - Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted, and your script will not be processed.

### Evaluation Criteria

Your SDK will be scored based on:

- **Detection Accuracy**: Correctly identifying automation frameworks by name
- **Consistency**: Maintaining accuracy across multiple test runs
- **Coverage**: Number of frameworks successfully detected
- **Minimum Requirement**: Must detect at least 2 of the 4 frameworks with 100% accuracy to qualify

### Scoring System

- **Per Framework**: Points awarded for consistent detection
- **Minimum Threshold**: Must achieve minimum score to rank on leaderboard

### Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other participants' SDKs
- 100% similarity = zero score
- Similarity above 60% will result in proportional score penalties based on the **detected similarity percentage**.

## Submission Guide

Follow 1~6 steps to submit your SDK.

1. **Navigate to the AB Sniffer v2 Commit Directory**

    ```bash
    cd redteam_core/miner/commits/ab_sniffer_v4
    ```

2. **Build the Docker Image**

    To build the Docker image for the AB Sniffer v2 submission, run:

    ```bash
    docker build -t my_hub/ab_sniffer_v4-miner:0.0.1 .

    # For MacOS (Apple Silicon) to build AMD64:
    DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/ab_sniffer_v4-miner:0.0.1 .
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
    docker push myhub/ab_sniffer_v4:0.0.1
    ```

5. **Retrieve the SHA256 Digest**

    After pushing the image, retrieve the digest by running:

    ```bash
    docker inspect --format='{{index .RepoDigests 0}}' myhub/ab_sniffer_v4:0.0.1
    ```

6. **Update active_commit.yaml**

    Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

    ```yaml
    - ab_sniffer_v4---myhub/ab_sniffer_v4@<sha256:digest>
    ```

---

## 📑 References

- Docker - <https://docs.docker.com>
