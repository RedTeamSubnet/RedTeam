---
title: Submission Comparison
tags: [comparison, concepts, scoring]
---

# 🔍 Submission Comparison

## Overview

The comparison process is a critical part of the RedTeam evaluation lifecycle. It ensures that every submission is unique, original, and meets the quality standards required for scoring. This stage follows [Validation](validation.md) and precedes the final [Scoring](dashboard.md#submission-status-lifecycle) and acceptance check.

## How Comparison Works

When a new submission is received and passes validation, it undergoes a similarity analysis against a specific subset of existing submissions to ensure it is not a duplicate or a minor modification of an existing solution.

### 1. The Comparison Pool

Your script is compared against a dynamic **Reference Pool** consisting of:

- **All Accepted Submissions**: Any submission that has successfully passed validation and scoring in the past.
- **Same-Day Submissions**: All submissions made on the current calendar day, regardless of their final status.

### 2. Sequential Logic (Same-Day)

Within the "Same-Day" group, submissions are processed in the order of their **committed timestamp**. This means your comparison pool depends on your submission's position in the daily queue:

| Submission Order | Comparison Pool |
| :--- | :--- |
| **1st of the day** | Historical accepted submissions only. |
| **2nd of the day** | Historical + 1st submission of the day. |
| **3rd of the day** | Historical + 1st and 2nd submissions of the day. |

!!! info "Fairness Note"
    This chronological approach ensures that earlier commits act as a reference for later ones, preventing multiple miners from submitting the same "leaked" or common solution on the same day and expecting full credit.

---

## Scoring and Thresholds

After analysis, the engine assigns a similarity score between **0.0 and 1.0** (where 1.0 is an identical match).

### The "Zero" Rule

A comparison score of **0** always indicates a failure or error during the comparison process (e.g., a processing timeout or a malformed script).

- **Behavior**: The system **always skips** these results.
- **Impact**: A 0 will never trigger a similarity penalty or rejection because it does not represent an actual similarity measurement.

### Acceptability Thresholds

Each challenge defines its own sensitivity to similarity. If a miner's script exceeds the **Maximum Acceptable Comparison Score** defined for that challenge, it is skipped from scoring entirely.

#### Same-UID vs. Different-UID

The system applies different thresholds depending on the relationship between miners:

- **Different UID**: Standard thresholds apply to ensure you aren't copying other miners' work.
- **Same UID**: Thresholds are typically **lower**.
    - **Why?** When you update your own script, the system requires a meaningful improvement rather than a trivial edit.
    - **Thresholds**: Each challenge has its own specific same-uid threshold (often around **0.9** for same-miner updates vs **0.7** for different miners).

---

## Examples

### Example 1: Pool Selection

Suppose the following state exists in the database:

- **10 submissions** have been **Accepted** in the last month.
- **10 submissions** were made **Today** before your commit.
- **Result**: Your submission will be compared against a total of **20** scripts (10 historical + 10 today).

### Example 2: Chronological Comparison

Three miners (A, B, and C) submit solutions for the same challenge at different times today:

1. **Miner A** (10:00 AM): Compares only against historical accepted submissions.
2. **Miner B** (11:00 AM): Compares against historical submissions + **Miner A**.
3. **Miner C** (12:00 PM): Compares against historical submissions + **Miner A** + **Miner B**.

### Example 3: Threshold Application

Imagine a challenge with an "Acceptable Score" of **0.7**:

- **Miner A** gets a similarity score of **0.75** against another miner.
    - **Result**: ❌ **Skipped** (Too similar).
- **Miner B** gets a similarity score of **0.65**.
    - **Result**: ✅ **Scored** normally.

---

## Summary Table

| Feature | Logic |
| :--- | :--- |
| **Reference Pool** | Accepted + Same-Day Submissions |
| **Ordering** | By Committed Timestamp |
| **Score Range** | 0.0 (Error/Skip) to 1.0 (Identical) |
| **Same UID Threshold** | Stricter (requires significant changes) |
| **Different UID Threshold** | Standard (prevents plagiarism) |

!!! tip "Reducing Similarity"
    To avoid high similarity scores, focus on unique logic and implementation strategies rather than just renaming variables or changing formatting. Meaningful improvements to the core algorithm are the best way to ensure your submission is unique.
