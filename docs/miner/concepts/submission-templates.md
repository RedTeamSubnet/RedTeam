---
title: "Submission Templates"
tags: [submission, templates]
---

# 🧩 Submission Templates

## Overview

Submission templates in each challenge repository are standardized structures that miners use to package their solutions for RedTeam challenges. They provide a complete, ready-to-use framework that defines how your code will communicate with the RedTeam validation system.

## Example Components

A complete submission example consists of:

| Component | Purpose |
| --------- | ------- |
| `app.py` | Main application entry point with required API routes (fixed) |
| `requirements.txt` | Python dependencies and versions |
| `Dockerfile` | Container configuration for reproducible deployment |
| `<your-solution-code>` | Your custom implementation files specific to the challenge |

## How the Example Works

### Workflow

1. **Initialization**: Docker container is built and started, dependencies are installed
2. **Health Check**: Validation system calls `/health` to verify service readiness
3. **Challenge Resolution**: Validation system sends challenge data via `/solve` endpoint and processes response
4. **Shutdown**: Container is gracefully terminated after validation completes

## API Routes

Your submission must implement two essential API routes. These are fixed in `app.py` and should not be modified:

### `/health` (GET)

Returns service status:

```json
{
    "status": "ok"
}
```

### `/solve` (POST)

- **Input**: `MinerInput` object containing challenge data
- **Output**: `MinerOutput` object containing your solution
- **Must** match the exact schema defined for your challenge

!!! note "Data Types"
    Challenge-specific data types are defined in the `templates/commit/src/data_types.py` file in each challenge repository.

## Template Files - Do Not Modify

The following files are fixed and should **not be modified**:

- **`app.py`** - Main entry point with required API routes
- **`Dockerfile`** - Container configuration

!!! warning "Template Files Are Fixed"
    Modifying these files will cause scoring and validation failure.

## Key Constraints

| Requirement | Specification |
| ----------- | -------------- |
| **Port** | Must be 10002 |
| **Health Timeout** | 5 seconds |
| **Solve Timeout** | 5 seconds |
| **HTTP Status** | 200 for success |
| **Data Format** | JSON |
