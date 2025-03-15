# Humanize Behaviour v2 Submission Guide (Active after March 16th 2025 14:00 UTC)

## Overview

**Humanize Behaviour v2** is a challenge designed to test bot scripts' ability to mimic human behavior within a web UI form. It evaluates how effectively a bot can interact with the form, navigate UI elements, engage with form fields, and submit required data accurately and efficiently, with grading based on **mouse movement** and **keyboard interaction analysis.**

This challenge assesses the precision and sophistication of bot scripts in performing web-based tasks. Miners participating must demonstrate human-like interaction capabilities through their bot scripts when engaging with the web UI form.

---

## Example Code and Submission Instructions

Example code for the Humanize Behaviour v2 can be found in the [`redteam_core/miner/commits/humanize_behaviour_v2/src/bot/bot.py`](../../redteam_core/miner/commits/humanize_behaviour_v2/src/bot/bot.py) file.

### Technical Requirements

- Python 3.10
- Ubuntu 24.04
- Docker container: selenium/standalone-chrome:4.28.1

### Core Requirements

1. Use our template from [`redteam_core/miner/commits/humanize_behaviour_v2/src/bot/bot.py`](../../redteam_core/miner/commits/humanize_behaviour_v2/src/bot/bot.py)
2. Keep the `run_bot()` function signature unchanged
3. Your bot must:
   - Work with the provided Selenium driver
   - Follow the click sequence specified in `config`
   - Input text into designated fields
   - Submit the form successfully

### Key Guidelines

- **Driver Usage**: Stick to the provided Selenium driver to ensure proper evaluation
- **Action Sequence**: Follow the provided `config` order precisely - deviations will result in a zero score
- **Click Behavior**:
    - Only click at specified locations
    - Additional clicks for input fields and submit buttons are allowed
    - Wrong click order = form submission failure
- **Text Input**:
    - Use text from the `config`
    - Locate fields by their `id` or `name`
    - Maintain the specified input order
- **Technical Setup**:
    - Enable headless mode
    - Save the login-button click for last
    - List dependencies in [`requirements.txt`](../../redteam_core/miner/commits/humanize_behaviour_v2/src/bot/requirements.txt)
    - Use amd64 architecture (ARM64 at your own risk)

### Evaluation Criteria

Your bot will be scored on these human-like behaviors:

- Mouse Movement Velocity Variation
- Mouse Movement Speed
- Mouse Movement Velocity Profiles between clicks
- Mouse Movement Granularity (average pixel per movement)
- Mouse Movement Count within the session
- Mouse Movement Trajectory Linearity
- Keypress Behavior Pattern (typing speed and variations)

### Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' code
- 100% similarity = zero score
- >60% similarity = significant score reduction
- Note: We don't compare against your previous humanize_behavior_v2 submissions

## Submission Guide

Follow 1~6 steps to submit your script.

1. **Navigate to the Humanize Behaviour v2 Commit Directory**

```bash
cd redteam_core/miner/commits/humanize_behaviour_v2
```

2. **Build the Docker Image**

To build the Docker image for the Humanize Behaviour v2 submission, run:

```bash
docker build -t my_hub/humanize_behaviour-miner:0.0.1 .

# For MacOS (Apple Silicon) to build AMD64:
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/humanize_behaviour-miner:0.0.1 .
```

3. **Log in to Docker**

Log in to your Docker Hub account using the following command:

```bash
docker login
```

Enter your Docker Hub credentials when prompted.

4. **Push the Docker Image**

Push the tagged image to your Docker Hub repository:

```bash
docker push myhub/humanize_behaviour:0.0.1
```

5. **Retrieve the SHA256 Digest**

After pushing the image, retrieve the digest by running:

```bash
docker inspect --format='{{index .RepoDigests 0}}' myhub/humanize_behaviour:0.0.1
```

6. **Update active_commit.yaml**

Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

```yaml
- humanize_behaviour---myhub/humanize_behaviour@<sha256:digest>
```

---

## 📑 References

- Docker - <https://docs.docker.com>
