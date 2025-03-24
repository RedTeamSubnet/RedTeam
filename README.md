# RedTeam Subnet: Improved Security Through Decentralized Innovation

## Overview

The RedTeam subnet by Innerworks is a decentralized platform designed to drive innovation in cybersecurity through competitive programming challenges. The subnet incentivizes miners to develop and submit code solutions to various technical challenges, with a focus on enhancing security. These solutions can be integrated into real-world products to improve their security features.

### Dashboard: <https://dashboard.theredteam.io>

![Overview](./docs/assets/overview.svg)

## Subnet Functionality

RedTeam's subnet now operates with a performance-based approach, encouraging continuous improvement and rewarding miners based on the quality and originality of their solutions. Every time a miner submits a solution, it is evaluated not just by how well it performs, but also by how much new value and innovation it brings to the subnet.

Miners can submit code solutions to challenges, but there's a key rule to prevent copying or plagiarism: we have a similarity checking system in place. This system compares new submissions with both past solutions and submissions made on the same day. Only unique, innovative contributions will be accepted, ensuring that the focus remains on continuous improvement and fresh ideas.

While the best solutions are still rewarded with higher scores, we use a softmax function to normalize these scores. This ensures that miners who make significant improvements are rewarded more fairly. This system is designed to be open but still motivates active, meaningful participation.

Submissions are scored once a day, based on their quality and innovation. The system checks each new submission for originality by comparing it to previously accepted solutions. Re-submitting the same idea or copying a past solution without adding new value or improvements will result in rejection. This encourages miners to keep innovating and bringing fresh ideas to the table, rather than recycling previous solutions.

## Scoring System: Fair, Dynamic, and Motivating

We've introduced an exciting new way to score miners that rewards innovation and long-term engagement. Here's how the new scoring system works:

### How the Score is Calculated

When miners participate in challenges, their performance is evaluated based on their solutions. The scoring system has three key components, each designed to reward different aspects of participation:

1. **Challenge Score (75%)**: The majority of the score comes from how well the miner's solution performs in a challenge. The system compares each miner's solution with others and awards higher points for more innovative and effective solutions. Better solutions get a larger share of the points, thanks to the use of a softmax function.

2. **Holding Alpha (15%)**: A small portion of the score is based on how much Alpha (our network's token) a participant is holding. This encourages participants to stay invested and engaged in the network, providing extra motivation to keep working on the challenges.

3. **New Participant Bonus (10%)**: We want to encourage newcomers to join and get involved, so we offer a bonus for newly registered participants. This bonus gradually decreases over time as the participants become more experienced and integrated into the community.

Each of these components is normalized to ensure fairness, and then combined into one final score using the formula:

- **Final Score = (75% * Challenge Score) + (15% * Alpha Holding Score) + (10% * New Participant Bonus)**

This dynamic approach ensures that miners are rewarded for both their immediate contributions and long-term participation.

## Validator Setup

[Read the full documentation](./docs/1.validator.md)

## Miner Setup

[Read the full documentation](./docs/2.miner.md)
