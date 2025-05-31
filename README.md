# RedTeam Subnet: Improved Security Through Decentralized Innovation

## Overview

The RedTeam subnet by Innerworks is a decentralized platform designed to drive innovation in cybersecurity through competitive programming challenges. The subnet incentivizes miners to develop and submit code solutions to various technical challenges, with a focus on enhancing security. These solutions can be integrated into real-world products to improve their security features.

### Dashboard: <https://dashboard.theredteam.io>

![Overview](./docs/assets/images/diagrams/overview.svg)

## Subnet Functionality

RedTeam's subnet now operates with a performance-based approach, encouraging continuous improvement and rewarding miners based on the quality and originality of their solutions. Every time a miner submits a solution, it is evaluated not just by how well it performs, but also by how much new value and innovation it brings to the subnet.

Miners can submit code solutions to challenges, but there's a key rule to prevent copying or plagiarism: we have a similarity checking system in place. This system compares new submissions with both past solutions and submissions made on the same day. Only unique, innovative contributions will be accepted, ensuring that the focus remains on continuous improvement and fresh ideas.

While the best solutions are still rewarded with higher scores, we use a softmax function to normalize these scores. This ensures that miners who make significant improvements are rewarded more fairly. This system is designed to be open but still motivates active, meaningful participation.

Submissions are scored once a day, based on their quality and innovation. The system checks each new submission for originality by comparing it to previously accepted solutions. Re-submitting the same idea or copying a past solution without adding new value or improvements will result in rejection. This encourages miners to keep innovating and bringing fresh ideas to the table, rather than recycling previous solutions.

## Scoring System: Fair, Dynamic, and Motivating

We've introduced an exciting new way to score miners that rewards innovation and long-term engagement. Here's how the new scoring system works:

### How the Score is Calculated

When miners participate in challenges, their performance is evaluated based on their solutions. The scoring system consists of three key components:

1. **Alpha Burn (50%)**: This mechanism reserves 50% of the alpha to maintain high subnet alpha and mitigate current inflation effects. Once the alpha reaches sufficient strength, the mechanism will be adjusted to incentivize staking miners. This approach helps maintain the subnet's value proposition.

2. **Decay Mechanism**: Submissions receive incentives for a limited period, requiring miners to regularly update their solutions to maintain their position in the subnet. Our comparison system identifies and penalizes duplicate submissions, encouraging continuous improvement and innovation.

3. **Fallback Mechanism**: When a new challenge is released, its weight allocation begins immediately. In cases where a challenge receives no valid submissions, its weights are automatically redistributed to other active challenges according to their respective weights, ensuring efficient resource allocation.

The final score is calculated using a normalized formula that combines these components:

- **Final Score = (50% * Challenge Score) + (50% * Alpha Burn)**

This balanced approach ensures that miners are rewarded both for their technical solutions and their contribution to the subnet's stability.

## Validator Setup

[Read the full documentation](./docs/1.validator.md)

## Miner Setup

[Read the full documentation](./docs/2.miner.md)

---

## Documentation

- **<https://docs.theredteam.io>**
