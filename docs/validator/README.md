---
title: Validator Overview
---

# Validator

!!! danger " CRITICAL ANNOUNCEMENT: Mandatory Migration"
    **Deadline:** You have one week to migrate your validator to the new repository.

    All validators must switch to the **[Official Validator Repository](https://github.com/RedTeamSubnet/validator)**. Support for the old setup is ending. If you do not migrate within the one-week window, your validator will stop working and you will lose VTRUST.

    **Action Required:**

    1. Stop your current validator.
    2. Follow the **[→ Installation Steps](https://github.com/RedTeamSubnet/validator/blob/main/README.md)** in the new repository immediately.

Welcome to the RedTeam Subnet Validator documentation. This guide will help you understand what validators do and how to run one on the RedTeam network.

!!! info "Main Validator Repository"
    The official validator repository with complete setup instructions is available at

    **[RedTeam Subnet Validator Repository →](https://github.com/RedTeamSubnet/validator)**
    
    This is the primary resource for running a validator node with all necessary documentation, configuration examples, and deployment scripts.

---

## What is a Validator?

Validators are essential participants in the RedTeam Subnet that:

- **Evaluate miners** - Send challenges to miners and assess their responses
- **Assign scores** - Rate miner performance based on quality metrics
- **Maintain consensus** - Work with other validators to ensure network integrity
- **Earn rewards** - Receive TAO emissions proportional to stake and performance

## Prerequisites

Before you begin, ensure you have:

- ✅ A registered Bittensor wallet with sufficient TAO staked
- ✅ Validator wallet registered on the RedTeam subnet
- ✅ A system meeting the [minimum requirements](#minimum-system-requirements)
- ✅ Basic knowledge of Docker or PM2 process management

---

## Minimum System Requirements

!!! warning "System Requirements"
    Below are the minimum system requirements for running a validator node:

    - **Server Type**: Bare Metal Server
    - **CPU**: 8-Core CPU
    - **RAM**: 32 GB
    - **Storage**: 512 GB
    - **OS**: Ubuntu 22.04 LTS or later
