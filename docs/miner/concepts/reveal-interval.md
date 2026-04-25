---
title: Commit Cooldown & Timing
tags: [reveal, submission, limits, incentives]
---

# 🕒 Commit Cooldown & Submission Timing

## Overview

RedTeam miner uses a Commit Cooldown delay to ensure fairness, prevent subnet spamming, and batch submissions for scoring. Understanding the submission lifecycle helps you use your daily slots and get scored reliably.

!!! info "Version Requirement"
    The **24-hour Commit Cooldown** is a recent update. To ensure your submissions are processed correctly under this window, you **must** be running miner version **v3.0.5** or higher.

## Submission Limits

To maintain network quality and prevent "trial-and-error" testing on production systems, the following limits apply:

- **1 Commit per Day**: Each miner can submit **one commit per challenge per 24-hour window**.
- **Latest Commit Wins**: If you submit multiple commits in the same day, **all earlier commits are canceled** and only the **latest** one is kept for scoring.

!!! danger "Spamming Prevention"
    The 1-commit limit prevents trial-and-error testing in production and keeps the subnet fair. If you push multiple commits in a day, the earlier ones are canceled and you still only get one scored attempt.

## The Commit Cooldown Lifecycle

The path from `git push` to a dashboard score typically takes a little over **24 hours**.

### 1. Commit Cooldown (Delay) 24 Hours

Once submitted, your code remains encrypted for approximately **24 hours**. During this time, it is visible on the dashboard as `encrypted_commit:...`.

### 2. Scoring & Evaluation (After Cooldown)

After the cooldown ends, the [Comparison](comparison.md), [Validation](validation.md), and Scoring engines process your code in a batch. This phase starts after the 24-hour delay and may take some additional time depending on network load.

| Phase | Duration | Dashboard Status |
| :--- | :--- | :--- |
| **Submission** | Instant | Pending |
| **Commit Cooldown (Decryption)** | ~24 Hours | Reveal / Processing |
| **Scoring** | After cooldown | Scored / Accepted / Rejected |
| **Total Time** | **~24+ Hours** | Final Result Visible |

---

## 🛠️ Troubleshooting Decryption Errors

### Key-Ciphertext Mismatch

The RedTeam subnet uses a **Commit-and-Reveal** scheme:

1. **Commit Phase**: The miner sends an `encrypted_commit` (ciphertext) to the validator. The decryption key remains secret on the miner's side.
2. **Reveal Phase**: After the Commit Cooldown, the miner automatically moves the key to `public_keys`, allowing the validator to decrypt the commit.

**The Issue**: If you update your `active_commit.yaml` with a new Docker hash for an existing challenge *before* the previous one has finished its reveal cycle, the miner generates a new ciphertext but the validator might still see an old key. This mismatch causes `InvalidToken` or decryption errors.

### How to Avoid Corruption

1. **Never Change a "Pending" Commit**: Do not update a challenge's Docker hash in `active_commit.yaml` until the validator has successfully decrypted the previous one.
    - **Check Logs**: Wait for: `Revealed commit: <hash>, <challenge_name>`.
    - **Check Dashboard**: Ensure status shows **Decrypted** or **Scored** before pushing an update to the same challenge.
2. **Versioning Your Submissions**: Challenge names in `active_commit.yaml` (e.g., `ab_sniffer_v5`, `humanize_behaviour_v5`) are fixed and cannot be changed. To avoid corruption, do not overwrite the Docker hash in your configuration while a reveal is pending. Instead, version your Docker images/tags and only update the configuration after the previous submission is scored.
    - **❌ Avoid**: Updating `active_commit.yaml` with a new hash for the same challenge before the 24-hour cooldown is complete.
3. **Clean State (Emergency Only)**: If you accidentally corrupted your local state, you can clear the miner's persistence file to force a full re-submission.
    
    !!! warning "Reset Warning"
        This resets the Commit Cooldown for **all** challenges. You will have to wait another 24+ hours before scoring begins.

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

1. **Submit Your Best Version**: You only get one scored commit per day.
2. **Avoid Re-pushing**: If you push again the same day, your earlier commit is canceled and only the latest one is scored.
3. **Local Testing First**: Use the [Testing Manuals](../../challenges/README.md) to verify your script before pushing.
4. **Timing Your Pushes**: Ensure your final commit is pushed at least **24+ hours before 2:00 PM UTC** to hit the daily cutoff.

!!! tip "Dashboard Visibility"
    If you do not see your submission transition to "Scored" within 24-36 hours, check the **Note** column on the dashboard for potential processing errors or validation failures.
