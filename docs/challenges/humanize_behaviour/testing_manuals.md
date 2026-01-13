---
title: Testing Manual
---

# Humanize Behaviour v5 Testing Manual

This manual provides instructions for testing the Humanize Behaviour v5 challenge using Docker and Docker Compose.

---

## Overview

- Tests bot script's ability to mimic human interaction with a Web UI form  
- Includes trajectory similarity check between sessions  
- Uses Docker and Docker Compose for easy submission and testing  

---

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed  
- Git (for cloning the repository)  

---

### Step 0: Clone the Repository

```bash
git clone https://github.com/RedTeamSubnet/humanize-behaviour-challenge.git humanize_behaviour
cd humanize_behaviour
```

### Step 1: Provide Your Scripts

- Paste your bot script into `bot.py`  
- Add your requirements to `requirements.txt`  

---

### Step 2: Setup

Copy and configure the compose override file:

```bash
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml
```

---

### Step 3: Start the Challenge Server

> [!NOTE]
> If something is changed in `src` on the host system, it will be changed inside the container too.

```bash
docker compose up -d 
```

---

### Step 4: Test Your Bot

- Visit: [http://localhost:10001/docs](http://localhost:10001/docs)
- Test your bot using the `/score` endpoint

---

## Important Notes

- The server runs on port `10001` by default
- Make sure port `10001` is available on your system
- The challenge includes trajectory similarity checks between sessions
- All interactions are logged for analysis

---

## Troubleshooting

If you encounter issues:

- Check if Docker is running
- Verify port `10001` is not in use
- Check Docker logs using:

```bash
docker compose logs
```

- Ensure you have proper permissions to run Docker commands

---

## References

> A bind mount links a directory from the host system directly into the container.  
> Any changes made to the mounted folder on the host are instantly reflected inside the container, and vice versa.  
> This is useful for live development, testing, and debugging without rebuilding images.

- Reference: [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
