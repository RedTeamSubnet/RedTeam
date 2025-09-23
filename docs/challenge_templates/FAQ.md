---
title: Frequently Asked Questions
---

# Frequently Asked Questions

## Submission Issues

### Q1: Why was my submission rejected for high similarity?
Your submission matched either:
- Your own last submission (**≥ 0.9** similarity)
- Another miner's submission (**≥ 0.7** similarity)

### Q2: What happens if I submit the same code twice?
Your latest submission overwrites the previous one. Identical submissions are rejected.

### Q3: Can I slightly improve my last submission and resubmit?
Yes, but changes must reduce similarity below **0.9**. Small edits usually aren't sufficient.

### Q4: Can I submit multiple commits for the same challenge?
No. Submit only one commit per challenge at a time to avoid conflicts.

## Scoring & Process

### Q5: How is similarity checked?
The **scoring logic is classified**. Each script is compared with every other script in the database.

### Q6: How long does scoring take?
Up to **48 hours** for revealing and scoring. If accepted, wait until you see emissions on [taostats.io](https://taostats.io) before resubmitting.

### Q7: Can I change my reveal interval?
Yes, modify your miner code:

**File:** `redteam_core/constants.py` → [line 161](https://github.com/RedTeamSubnet/RedTeam/blob/3a32852c2e9476f802aa1621af521f0f970839bc/redteam_core/constants.py#L161)

**Default:** `3600 * 24` (24 hours)

!!! NOTE
    Lowering the interval may score sooner, but still allow 48 hours before assuming an issue.

## Testing

### Q8: How can I test my submission before sending it?
Use the `testing_manual.md` file in the challenge's `docs` folder to verify your script gets a valid score before submission.

---

## ✅ Submission Checklist

Before submitting your challenge solution:

1. **🧪 Run Tests First**
   - Follow `testing_manual.md` in the challenge's `docs` folder

2. **🎯 Ensure Unique Code**
   - Must differ substantially from your past work and others'

3. **📝 One Commit per Challenge**
   - No multiple commits for the same challenge simultaneously

4. **💡 Make Meaningful Changes**
   - Improve logic, not just formatting

5. **📊 Respect Similarity Limits**
   - Same miner: reject if ≥ **0.9**
   - Different miner: reject if ≥ **0.7**

6. **⏰ Wait After Submit**
   - Up to **48 hours** for scoring

7. **💰 Check Emissions**
   - If accepted, wait for emissions to appear before resubmitting

8. **⚙️ Reveal Interval (Optional)**
   - Adjust in `constants.py` (line 161), but respect the 48-hour window

9. **📋 Review Guidelines**
   - Check [submission rules](https://github.com/RedTeamSubnet/RedTeam#:~:text=Re%2Dsubmitting%20the%20same%20idea...) before pushing
