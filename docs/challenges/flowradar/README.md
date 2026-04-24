---
title: FlowRadar VPN Detection Challenge
---

# FlowRadar VPN Detection Challenge

## Overview

FlowRadar is a VPN detection challenge. Miners receive network flow features as JSON and must return a single boolean indicating VPN usage.

## What You Build

You submit a single `submission.py` file that implements a VPN detector. The system sends one network flow at a time to your API and expects:

```json
{
  "is_vpn": true
}
```

## Data

- **Training data**: ~51k rows extracted from open-source MIT datasets (collected in 2022)
- **Testing data**: internal production dataset collected with modern top VPN providers

Training data is for local experimentation. Testing data is used for production scoring.

## Challenge Flow (High Level)

1. Your submission is packaged into a container with a `/vpn_detector` endpoint.
2. The scoring system iterates through flow rows and posts each flow as JSON.
3. Your response is compared against ground-truth labels.
4. Score is computed using F1.

## Challenge Versions

- [v1 (Active)](./v1.md)

## Resources

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md)
- [Dashboard](../../miner/concepts/dashboard.md)

## References

- RedTeam Subnet: <https://www.theredteam.io>
- FastAPI: <https://fastapi.tiangolo.com>
