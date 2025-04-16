# Humanize Behaviour v3 Submission Guide (Active after March 18th 2025 14:00 UTC)

## Overview

**Humanize Behaviour v3** tests bot scripts' ability to mimic human interaction with a web UI form with dynamic movements accross different sessions. It evaluates how well a bot navigates UI elements, interacts with form fields, and submits data without being caught by the bot detection system, based on  **mouse movement**, **keyboard interaction analysis.** and **mouse movement similarities over sessions**

Miners must demonstrate precise, human-like interactions through their bot scripts when completing the form. And also they have to keep in mind their bots should not make same mouse movement trajectory in each iteration

---

## Example Code and Submission Instructions

Example codes for the Humanize Behaviour v3 can be found in the [`redteam_core/miner/commits/humanize_behaviour_v3/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/humanize_behaviour_v3/) directory.

### Technical Requirements

- Python 3.10
- Ubuntu 24.04
- Docker container: selenium/standalone-chrome:4.28.1

### Core Requirements

1. Use our template from [`redteam_core/miner/commits/humanize_behaviour_v3/src/bot/bot.py`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/humanize_behaviour_v3/src/bot/bot.py)
2. Keep the `run_bot()` function signature unchanged
3. Your bot must:
   - Work with the provided Selenium driver
   - Input text into designated fields
   - Submit the form without errors

### Key Guidelines

- **Driver Usage**: Stick to the provided Selenium driver to ensure proper evaluation
- **Action Sequence**: Follow the provided `ACTIONS LIST` order. Clicking it at the start or in the middle will prematurely submit data and result in a zero score due to invalid action flow.
- **Click Behavior**:
    - Only click at specified locations
    - Additional clicks for input fields and submit buttons are allowed
    - Wrong click order will result in form submission failure.
- **Text Input**:
    - Locate fields by their `id`
    - Use text from the `ACTIONS LIST`
    - Maintain the specified input order
- **Cross-Session Behavior Variation**:
    - Your bot must demonstrate different movement patterns across multiple evaluation sessions
    - While click targets remain the same, mouse trajectories should vary naturally between sessions
    - Similar movement patterns across sessions will be flagged as bot-like behavior
    - Implement randomization strategies that mimic natural human variability
- **Technical Setup**:
    - Enable headless mode
    - List dependencies in [`pip_requirements`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/humanize_behaviour_v3/src/bot/requirements.txt). See the limitations for dependencies below.
    - Use amd64 architecture (ARM64 at your own risk)
    - If your script requires system-level dependencies, add them to `system_deps` field as ubuntu packages (concatenate with space if multiple packages are needed `"package1 package2"`) in `/solve` endpoint reponse.
- **Limitations**
    - Your script must not exceed 2,000 lines. If it does, it will be considered invalid, and you will receive a score of zero.
    - Your dependencies must be older than January 1, 2025. Any package released on or after this date will not be accepted, and your script will not be processed.

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

- All submissions are compared against other miners' script
- 100% similarity = zero score
- Similarity above 60% will result in proportional score penalties based on the **detected similarity percentage**.
- Note: Comparisons are only made against other miners submissions, not your own previous Humanize Behaviour v3 entries.

## Submission Guide

Follow 1~6 steps to submit your script.

1. **Navigate to the Humanize Behaviour v3 Commit Directory**

    ```bash
    cd redteam_core/miner/commits/humanize_behaviour_v3
    ```

2. **Build the Docker Image**

    To build the Docker image for the Humanize Behaviour v3 submission, run:

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
