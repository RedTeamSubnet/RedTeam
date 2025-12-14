---
title: Anti-Detect Automation Detection
---

# Anti-Detect Automation Detection (AAD)

## 1. Overview

The **Anti-Detect Automation Detection (AAD)** challenge evaluates a participant’s ability to **reliably detect browser automation frameworks operating inside anti-detect browsers**, while **preserving human safety**.

All evaluations are executed inside **NST-Browser**, where:

* Browser fingerprints are masked
* Profiles are fresh per run
* Automation attempts to closely mimic real users

---

## 2. Anti-Detect Environment

Each evaluation run uses:

* A **fresh NST-Browser profile**
* An **isolated Docker container per framework**
* No shared state between runs

This environment simulates real-world anti-detect usage where static signals are unreliable.
Only **runtime behavior and orchestration patterns** remain detectable.

---

## 3. Detection Philosophy

AAD follows one strict rule:

> **Detect how automation behaves, not how it identifies itself.**

### Allowed Signals

* WebSocket control patterns
* Runtime automation artifacts
* Orchestration timing anomalies
* Behavioral impossibilities for humans

---

## 4. Evaluation Flow

Each submission is evaluated as follows:

1. **Submission Received**
   Detection scripts are submitted via the `/score` endpoint.

2. **Task Generation**
   A randomized sequence is created consisting of:

   * Multiple runs per automation framework
   * Randomly injected human interactions

3. **NST-Browser Launch**
   A clean NST-Browser instance is started for each task.

4. **Automation / Human Execution**

   * Automation frameworks connect via WebSocket control
   * Humans manually interact with the page

5. **Detection Phase**

   * Scripts may emit detection payloads to `/_payload`
   * Silence during human interaction is expected

6. **Scoring**

   * Results are aggregated, normalized, and returned

---

## 5. Target Frameworks

Participants must submit **one detection script per framework**:

* `nodriver`
* `playwright`
* `patchright`
* `puppeteer`

Missing scripts invalidate the submission.

---

## 6. Submission Format

Submissions must follow this structure:

```json
{
  "detection_files": [
    { "file_name": "nodriver.js", "content": "/* logic */" },
    { "file_name": "playwright.js", "content": "/* logic */" },
    { "file_name": "patchright.js", "content": "/* logic */" },
    { "file_name": "puppeteer.js", "content": "/* logic */" }
  ]
}
```

### Rules

* File names must match framework names exactly
* Each file detects **only its own framework**
* No extra files or outputs are allowed

---

## 7. Payload Rules

* Detection results are sent to the internal `/_payload` endpoint
* Payloads must represent **confirmed detection only**
* **Any payload during human interaction counts as a mistake**

Logs do not affect scoring.
Only payloads are evaluated.

---

## 8. Scoring System (Code-Accurate)

AAD scoring is continuous, normalized, and strict, combining three main components before being normalized into a final score.

*   **Human Accuracy:** This is the most critical component. Your submission must not flag real human users as bots. You are allowed a maximum of 2 mistakes; exceeding this limit results in an immediate **final score of 0.0**. For scoring, you start with 1.0 point, and each mistake reduces this component by 0.1.

*   **Automation Accuracy:** This measures your overall ability to correctly classify tasks as either "bot" or "human". It is calculated with the formula `(total_tasks - total_misses) / total_tasks`, where `total_misses` includes both failing to detect a bot and incorrectly flagging a human.

*   **Framework Detection:** Your submission earns points for correctly identifying the specific automation framework being used. For each framework, you are tested multiple times. You only earn **1 full point** for a framework if you detect it perfectly in **all of its runs**. A single missed detection or a collision (reporting more than one framework) for a given framework will result in **0 points** for that framework.

Finally, all the points are summed and normalized to produce your final score between 0.0 and 1.0 using the formula:
`Final Score = (Human Accuracy Score + Automation Score + Framework Points) / (Number of Frameworks + 1 Human + 1 Automation)`
## 9. Example

Assume:

*   4 frameworks
*   Perfect human accuracy → 1.0
*   Automation accuracy → 0.9
*   2 frameworks detected perfectly → 2.0 points

```
Final Score = (1.0 + 0.9 + 2.0) / (4 + 1 + 1)
            = 3.9 / 6
            = 0.65
```

Any excessive human misclassification would reduce this to **0.0**.

---

## 10. Technical Constraints

* JavaScript (ES6+)
* NST-Browser only
* Docker (amd64 recommended)
* Stateless execution
* No persistence between runs

---

## 11. Plagiarism Policy

* Submissions are compared against others
* 100% similarity → score = 0
* Similarity above 60% incurs proportional penalties

---


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
