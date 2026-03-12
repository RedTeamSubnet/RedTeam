---
title: Reveal & Timing
tags: [reveal, submission, limits, incentives]
---

# 🕒 Reveal & Submission Timing

## Overview

RedTeam miner uses a delayed reveal mechanism to ensure fairness and prevent real-time strategy leaks. Understanding the submission lifecycle is essential for maximizing your daily slots and ensuring your work is properly scored.

!!! info "Version Requirement"
    The **3-hour reveal interval** is a recent update. To ensure your submissions are processed correctly under this window, you **must** be running miner version **v3.0.5** or higher.

## Submission Limits

To maintain network quality and prevent "trial-and-error" testing on production systems, the following limits apply:

- **2 Commits per Day**: Each miner can submit a maximum of two commits per challenge within a 24-hour window.
- **One-at-a-Time Rule**: You should only have **one active submission** per challenge at any given time.
    - **Overwriting**: If you submit a new commit while a previous one is still in the "Received" status, the new commit will **overwrite** the old one. The previous commit will never be scored, and you will have consumed one of your two daily slots.

!!! danger "Spamming Prevention"
    The 2-commit limit is designed to allow you to fix critical issues discovered after your first submission is scored. It is **not** intended for simultaneous testing or spamming variations of a solution. Miners who attempt to bypass these limits or push multiple updates before scoring are treated as "testing in production," which can lead to status rejections or rate limiting.

## The Reveal Lifecycle

The path from `git push` to a dashboard score typically takes up to **6 hours**.

### 1. Decryption (Reveal) 3 Hours

Once submitted, your code remains encrypted for approximately **3 hours**. During this time, it is visible on the dashboard as `encrypted_commit:...`.

### 2. Scoring & Evaluation 3 Additional Hours

After decryption, the [Comparison](comparison.md), [Validation](validation.md), and Scoring engines process your code. This phase can take an additional 3 hours depending on network load.

| Phase | Duration | Dashboard Status |
| :--- | :--- | :--- |
| **Submission** | Instant | Pending |
| **Reveal (Decryption)** | ~3 Hours | Reveal / Processing |
| **Scoring** | ~3 Hours | Scored / Accepted / Rejected |
| **Total Time** | **~6 Hours** | Final Result Visible |

---

## 🛠️ Troubleshooting Decryption Errors

### Key-Ciphertext Mismatch

The RedTeam subnet uses a **Commit-and-Reveal** scheme:

1. **Commit Phase**: The miner sends an `encrypted_commit` (ciphertext) to the validator. The decryption key remains secret on the miner's side.
2. **Reveal Phase**: After the reveal interval, the miner automatically moves the key to `public_keys`, allowing the validator to decrypt the commit.

**The Issue**: If you update your `active_commit.yaml` with a new Docker hash for an existing challenge *before* the previous one has finished its reveal cycle, the miner generates a new ciphertext but the validator might still see an old key. This mismatch causes `InvalidToken` or decryption errors.

### How to Avoid Corruption

1. **Never Change a "Pending" Commit**: Do not update a challenge's Docker hash in `active_commit.yaml` until the validator has successfully decrypted the previous one.
    - **Check Logs**: Wait for: `Revealed commit: <hash>, <challenge_name>`.
    - **Check Dashboard**: Ensure status shows **Decrypted** or **Scored** before pushing an update to the same challenge.
2. **Versioning Your Submissions**: Challenge names in `active_commit.yaml` (e.g., `ab_sniffer_v5`, `humanize_behaviour_v5`) are fixed and cannot be changed. To avoid corruption, do not overwrite the Docker hash in your configuration while a reveal is pending. Instead, version your Docker images/tags and only update the configuration after the previous submission is scored.
    - **❌ Avoid**: Updating `active_commit.yaml` with a new hash for the same challenge before the 3-hour reveal is complete.
3. **Clean State (Emergency Only)**: If you accidentally corrupted your local state, you can clear the miner's persistence file to force a full re-submission.
    
    !!! warning "Reset Warning"
        This resets the reveal interval for **all** challenges. You will have to wait another 3+ hours before scoring begins.

    ```bash
    # Default path for miner state in the mounted volume
    rm ./volumes/storage/agent-miner/data/commits/commit.pkl
    # After deleting, restart your miner node
    ```

---

## Incentive Distribution

Rewards follow a daily synchronization window:

- **Cutoff Time**: **2:00 PM UTC**
- **Process**: At this time, all validators pull the latest scored submissions.
- **Eligibility**: Your submission must be **Scored and Accepted** before 2:00 PM UTC to be included in that day's incentive calculation.

---

## Best Practices for Miners

1. **Submit Your Best Version**: Treat your first daily slot as your primary submission.
2. **Monitor the Dashboard**: Always wait until your first submission shows a final status (**Accepted**, **Rejected**, or **Invalid**) before pushing a second one.
3. **Local Testing First**: Use the [Testing Manuals](../../challenges/README.md) to verify your script before pushing.
4. **Timing Your Pushes**: Ensure your final commit is pushed at least **6-8 hours before 2:00 PM UTC** to hit the daily cutoff.

!!! tip "Dashboard Visibility"
    If you do not see your submission transition to "Scored" within 6-12 hours, check the **Note** column on the dashboard for potential processing errors or validation failures.
