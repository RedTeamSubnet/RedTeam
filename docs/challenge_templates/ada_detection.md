---
title: Anti-Detect Automation Detection
---

# Anti-Detect Automation Detection (AAD)

## 1. Overview

The **Anti-Detect Automation Detection (AAD)** challenge evaluates a participant’s ability to **reliably detect browser automation frameworks operating inside anti-detect browsers**, while **preserving human safety**.

All evaluations are executed inside **NST-Browser**, where:

* Browser fingerprints are masked
* Profiles are isolated per run
* Automation attempts to closely mimic real users

The challenge focuses on **behavioral detection**, not fingerprinting.

---

## 2. Anti-Detect Environment

Each evaluation run uses:

* A **fresh NST-Browser profile**
* An **isolated Docker container per framework**
* No shared state between runs

This environment simulates real-world anti-detect usage where static signals are unreliable.
Only **runtime behavior and orchestration patterns** remain detectable.

Any fingerprint-based solution will fail.

---

## 3. Detection Philosophy

AAD follows one strict rule:

> **Detect how automation behaves, not how it identifies itself.**

### Allowed Signals

* WebSocket control patterns
* Runtime automation artifacts
* Orchestration timing anomalies
* Behavioral impossibilities for humans

### Forbidden Signals

* Browser fingerprinting of any kind
* Canvas, audio, font, WebGL checks
* User-Agent or hardware assumptions
* Static environment heuristics

Violations result in **immediate disqualification**.

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

6. **Cleanup**

   * Containers and profiles are destroyed after each task

7. **Scoring**

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

AAD scoring is **continuous, normalized, and strict**.

### 8.1 Human Safety Score (≈ 0–1)

* Each human task must produce **no automation detection**
* If human mistakes exceed the allowed limit → **final score = 0**
* Otherwise:

    * 0 misses → **1.0**
    * Each miss reduces score by **0.1**

---

### 8.2 Automation Accuracy Score (0–1)

Measures how consistently automation presence is detected:

```
automation_score =
  (total_tasks - total_misses) / total_tasks
```

`total_misses` is a sum of:

1. Human tasks incorrectly flagged as automation.
2. Automation tasks that were not detected as automation.

This rewards correct **bot vs human** classification, independent of framework attribution.

---

### 8.3 Framework Detection Score (0–N)

* Each framework is tested **multiple times**.

* A framework earns **1 full point** only if it is detected correctly and without collision in **all of its repeated runs**.

* **A single missed detection or collision will result in 0 points for that framework.**

* While collisions technically grant 0.1 points during an intermediate calculation, they ultimately prevent the framework from receiving any points.

To illustrate the scoring for a framework (assuming 3 runs):

| Scenario (3 runs)           | Internal Count | Final Framework Points |
| :-------------------------- | :------------- | :--------------------- |
| 3 Correct Detections        | `3.0`          | `1.0`                  |
| 2 Correct, 1 Collision      | `2.1`          | `0.0`                  |
| 2 Correct, 1 Miss           | `2.0`          | `0.0`                  |
| Any scenario with a miss    | `< 3.0`        | `0.0`                  |

---

### 8.4 Final Score Formula

```
Final Score =
  (Human Score + Automation Score + Framework Points)
  /
  (Number of Frameworks + 1 Human + 1 Automation)
```

This normalization ensures scores fall within **0.0 – 1.0**.

---

## 9. Example

Assume:

* 4 frameworks
* Perfect human safety → 1.0
* Automation accuracy → 0.9
* 2 frameworks detected perfectly → 2.0 points

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

## 12. Final Notes

AAD reflects **real bot-mitigation conditions** under anti-detect environments.

There are no shortcuts:

* Fingerprints will fail
* Over-detection will fail
* Only precise behavioral detection survives

---
