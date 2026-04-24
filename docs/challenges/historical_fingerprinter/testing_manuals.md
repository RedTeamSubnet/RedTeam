---
title: Testing Manual
---

# Historical Fingerprinter Testing Manual

This manual provides instructions for testing the Historical Fingerprinter challenge using Docker and Docker Compose.

## Overview

- Tests are designed to evaluate the effectiveness of your detection scripts against the Historical Fingerprinter challenge.
- Uses Docker for easy submission and testing

## Quick Start Guide

### Prerequisites

- Docker
- Docker Compose

### Step 0: Clone the Repository [skip if you cloned already]

```bash
git clone git@github.com:RedTeamSubnet/historical-fingerprinter-challenge.git historical_fingerprinter
cd historical_fingerprinter
```

### Step 1: Provide Your all Scripts

- Paste all of your all 3 scripts into **src/hfp_challenge/challenge/fingerprinter/src/submissions** folder with matching names.

### Step 2: Update Configuration Files

```bash
cp .env.example .env
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml
```

### Step 3: Setting up environmental variables

- Change `HFP_CHALLENGE_API_KEY` with your own preferred API key. You can use any string as API key, but make sure to update it in your detection scripts as well.

### Step 4: Start the Challenge Server

```bash
docker compose up -d challenge-api
```

### Step 5: Test Your Detection Scripts

- Visit <https://localhost:10001/docs>
- Authenticate using provided authentication API that you put into the `.env` with `HFP_CHALLENGE_API_KEY` variable.
    ![alt text](https://github.com/RedTeamSubnet/historical-fingerprinter-challenge/blob/08e3deea03d551a5d97b9f93c41b7b31a5c2ee01/docs/images/image.png?raw=true)
- Test your detection files by running the `/score` endpoint
- Check your score and justification by running the `/results` endpoint

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
