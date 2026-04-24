---
title: Testing Manual
---

# FlowRadar VPN Detection Testing Manual

This manual provides instructions for testing the FlowRadar VPN detection challenge using Docker and Docker Compose.

## Overview

- Tests are designed to evaluate the effectiveness of your VPN detection implementation.
- Uses Docker for easy submission and testing

## Quick Start Guide

### Prerequisites

- Docker
- Docker Compose

### Step 0: Clone the Repository [skip if you cloned already]

```bash
git clone git@github.com:RedTeamSubnet/flowradar-challenge.git flowradar
cd flowradar
```

### Step 1: Provide Your `submission.py` Script

- Paste your `submission.py` script into **src/flr_challenge/challenge/flowradar/src** folder.

### Step 2: Update Configuration Files

```bash
cp .env.example .env
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml
```

### Step 3: Setting up environmental variables

- Change `FLR_CHALLENGE_API_KEY` with your own preferred API key. You can use any string as API key, but make sure to update it in your detection scripts as well.

### Step 4: Start the Challenge Server

```bash
docker compose up -d challenge-api
```

### Step 5: Test Your Detector Script

- Visit <https://localhost:10001/docs>
- Authenticate using provided authentication API that you put into the `.env` with `FLR_CHALLENGE_API_KEY` variable.
    ![alt text](https://github.com/RedTeamSubnet/historical-fingerprinter-challenge/blob/08e3deea03d551a5d97b9f93c41b7b31a5c2ee01/docs/images/image.png?raw=true)
- Test your detection files by running the `/score` endpoint

## Important Notes

- The server runs on port 10001 by default
- Make sure port 10001 is available on your system
- All interactions are logged for analysis. Miners can check logs by running `docker compose logs -f`
- All commands must be executed from challenge's root directory.
- If you want score justification, you can check all results with `results` endpoint after running the `score` endpoint.

## Troubleshooting

If you encounter issues:

1. Check if Docker is running
2. Verify port 10001 is not in use
3. Check Docker logs using `docker compose logs`
4. Ensure you have proper permissions to run Docker commands
5. If you got lower or higher score than expected, you can check the justification of your score by running `results` endpoint after running the `score` endpoint. You can also check the logs for more details on how your detection script performed against the test cases.
