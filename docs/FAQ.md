**Q1: Why was my submission rejected for high similarity?**
Because it matched either your own last submission (**≥ 0.9**) or another miner’s submission (**≥ 0.7**) too closely.

**Q2: What happens if I submit the same code twice?**
Your latest submission will overwrite your previous one. If it’s identical, it will be rejected.

**Q3: Can I slightly improve my last submission and resubmit?**
Yes — but changes must reduce similarity below **0.9**. Small edits usually aren’t enough.

**Q4: Can I submit multiple commits for the same challenge?**
No. Submit only one commit per challenge at a time to avoid conflicts.

**Q5: How is similarity checked?**
The **scoring logic is classified**. What we can share: each script is compared with every other script in the database.

**Q6: How long does scoring take?**
Up to **48 hours** for revealing and scoring. If accepted, wait until you see emissions on [taostats.io](https://taostats.io) before resubmitting.

**Q7: Can I change my reveal interval?**
Yes, in your miner code:
`redteam_core/constants.py` → [line 161](https://github.com/RedTeamSubnet/RedTeam/blob/3a32852c2e9476f802aa1621af521f0f970839bc/redteam_core/constants.py#L161)
Default: `3600 * 24` (24 hours). Lowering it may score sooner, but still allow 48 hours before assuming an issue.

**Q8: How can I test my submission before sending it?**
Use the `testing_manual.md` file in the `docs` folder of the challenge directory to verify your script gets a valid score before submission.

---

## **✅ Final Checklist Before Submitting**

1. **Run Tests First** – Follow `testing_manual.md` in the challenge’s `docs` folder.
2. **Unique Code** – Must differ substantially from your past work and others’.
3. **One Commit per Challenge** – No multiple commits for the same challenge at once.
4. **Meaningful Changes** – Improve logic, not just formatting.
5. **Similarity Limits** –

   * Same miner: reject if ≥ **0.9**
   * Different miner: reject if ≥ **0.7**
6. **Wait After Submit** – Up to **48 hours** for scoring.
7. **Emission Check** – If accepted, wait for emissions to appear before resubmitting.
8. **Reveal Interval** – Optional: adjust in `constants.py` (line 161), but still respect the 48-hour window.
9. **Guidelines** – Review [submission rules](https://github.com/RedTeamSubnet/RedTeam#:~:text=Re%2Dsubmitting%20the%20same%20idea...) before pushing.