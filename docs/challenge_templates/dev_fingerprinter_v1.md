# Device Fingerprinter v1 Submission Guide (Active after September [x]th 2025 10:00 UTC)

![thumnail](../assets/images/challenges/dev_fingerprinter_v1/thumbnail.png)

## Overview

**Device Fingerprinter v1** tests miners' ability to develop a browser SDK that can accurately detect the driver type used by bots interacting with a webpage.

Miners must create a JavaScript fingerprinter that can distinguish between different devices through device fingerprinting techniques, analyzing browser properties, behavior patterns, and technical signatures.

---

## Example Code and Submission Instructions

Example codes for the Device Fingerprinter v1 can be found in the [`redteam_core/miner/commits/dev_fingerprinter_v1/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/dev_fingerprinter_v1/) directory.

### Technical Requirements

- JavaScript (ES6+)
- Ubuntu 24.04
- Docker container support

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
- **Fingerprint Collection**:
    - Collect comprehensive browser and device properties
    - Analyze WebDriver signatures and automation artifacts
- **Data Processing**:
    - Generate unique, consistent fingerprint hashes
    - Process collected data efficiently
- **API Integration**:
    - Follow the provided API endpoint structure
    - Send properly formatted JSON payloads
    - Handle errors gracefully
- **Technical Setup**:
    - Use modern JavaScript (ES6+) features
    - List dependencies in [`requirements.txt`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/dev_fingerprinter_v1/requirements.txt)
    - Use **amd64** architecture
- **Limitations**
    - Your script must not exceed 2,000 lines. If it does, it will be considered invalid, and you will receive a score of zero.
    - Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted, and your script will not be processed.

### Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' scripts
- 100% similarity = zero score
- Similarity above 60% will result in proportional score penalties based on the **detected similarity percentage**.
- Note: Comparisons are only made against other miners submissions, not your own previous challenge entries.

## Submission Guide

Follow 1~6 steps to submit your script.

1. **Navigate to the Device Fingerprinter v1 Commit Directory**

    ```bash
    cd redteam_core/miner/commits/dev_fingerprinter_v1
    ```

2. **Build the Docker Image**

    To build the Docker image for the Device Fingerprinter v1 submission, run:

    ```bash
    docker build -t my_hub/dev_fingerprinter_v1-miner:0.0.1 .

    # For MacOS (Apple Silicon) to build AMD64:
    DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/dev_fingerprinter_v1-miner:0.0.1 .
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
    docker push myhub/dev_fingerprinter_v1:0.0.1
    ```

5. **Retrieve the SHA256 Digest**

    After pushing the image, retrieve the digest by running:

    ```bash
    docker inspect --format='{{index .RepoDigests 0}}' myhub/dev_fingerprinter_v1:0.0.1
    ```

6. **Update active_commit.yaml**

    Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

    ```yaml
    - dev_fingerprinter_v1---myhub/dev_fingerprinter_v1@<sha256:digest>
    ```

---

## 📑 References

- Docker - <https://docs.docker.com>
