---
title: "Incentive Mechanism"
tags: [incentive, mechanism, rewards]
---

# 💰 Incentive Mechanism

## Overview

Bittensor's incentive mechanism is the core economic engine that rewards miners for producing high-quality work in subnets. Miners earn TAO tokens through a competitive, performance-based system where validators evaluate their submissions and Yuma Consensus determines emission allocations. This mechanism ensures that miners are continuously incentivized to improve their solutions, driving innovation and quality across the network.

## How Miners Earn TAO Rewards

Miners earn TAO by participating in subnet challenges and achieving high performance scores. The reward system operates through a two-stage process:

### 1. Performance Evaluation
- **Validators** assess miner submissions according to subnet-specific criteria
- Each validator assigns **weights** (scores) to miners based on solution quality
- Weights range from 0.0 to 1.0, representing relative performance rankings

### 2. Emission Distribution
- **[Yuma Consensus](https://docs.learnbittensor.org/learn/yuma-consensus)** aggregates validator weights, weighted by stake
- Miners receive **41% of subnet emissions** proportional to their performance
- Emissions are distributed every **tempo** (approximately 360 blocks, ~72 minutes)

!!! info "Flow-Based Emissions"
    As of November 2025, Bittensor uses **flow-based emissions** where subnet TAO injections are determined by net TAO inflows (staking minus unstaking) rather than token prices. Subnets with positive net flows receive proportional emissions, while those with negative flows get zero.

## Role of Validators in Miner Rewards

Validators play a critical role in determining miner emissions:

- **Evaluation**: Validators test miner submissions against challenge requirements
- **Scoring**: Each validator produces a weight vector ranking all miners they've evaluated
- **Consensus Formation**: Weight matrices from all validators are processed by Yuma Consensus
- **Emission Calculation**: Validator stake influences the weight of their evaluations

Validators are incentivized to provide accurate, honest evaluations because:
- Inaccurate weights are penalized through **clipping** and **bond adjustments**
- Consistent consensus alignment builds stronger **EMA bonds** for higher future emissions

| Recipient | Share | Details |
|-----------|--------|---------|
| **Miners** | 41% | Proportional to Yuma Consensus scores |
| **Validators** | 41% | Based on bonds to high-performing miners |
| **Subnet Owner** | 18% | Fixed portion for maintenance and development |

## Reward Calculation for Miners

Miner TAO earnings are calculated through:

1. **Raw Score**: Validator-assigned weights (0.0-1.0)
2. **Aggregate Ranking**: Stake-weighted sum across all validators
3. **Share Calculation**: Proportion of total miner rankings in subnet
4. **Emission Amount**: 41% × Subnet TAO emission × Miner's share

```
Miner TAO = 0.41 × Subnet_TAO_Emission × (Miner_Ranking / Total_Rankings)
```

!!! tip "Maximizing Rewards"
    - Focus on consistent high-quality submissions
    - Avoid plagiarism (reduces final score via penalties)
    - Monitor validator consensus for feedback
    - Submit regularly during active periods (before decay)

### Performance Optimization
- **Quality over Quantity**: Single high-scoring submission often outperforms multiple mediocre ones
- **Continuous Improvement**: Older submissions decay over ~10-15 days, encouraging updates

!!! warning "Submission Replacement"
    Each new commit **immediately stops rewards** from previous submissions. Plan submission timing strategically to maximize earnings.

## Related Topics

- See [Mining in Bittensor](../miners) for registration and participation details
- See [Dashboard](dashboard.md) for monitoring submission performance and rewards
- See [Lifecycle](lifecycle.md) for the complete miner journey
- Visit [TAO.app](https://tao.app) for current subnet emissions and flows
- Review [Emissions documentation](https://docs.learnbittensor.org/learn/emissions) for technical details

The incentive mechanism creates a self-reinforcing cycle: better miner performance attracts more validators, leading to more accurate evaluations, higher emissions, and further network growth. Successful miners focus on delivering genuine value that validators recognize and reward.
