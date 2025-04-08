# Humanize Behaviour v1 Submission Guide (Active after Feb 12st 2025 14:00 UTC)

## Description

The **Humanize Behaviour v1** is designed to test the ability of a bot scripts to mimic human behaviour with a web ui form. The challenge measures how well the bot script can interact with the form and submit the required information.

This challenge is intended to evaluate the accuracy and efficiency of bot scripts in completing web-based tasks. It assesses the ability of the bot script to navigate through the UI elements, interact with form fields, and submit the required data.

Miners participating in this challenge should be capable of simulating human-like behaviour while interacting with the web ui form by bot script.

---

## Example Code and Submission Instructions

Example code for the Humanize Behaviour v1 can be found in the [`redteam_core/miner/commits/humanize_behaviour_v1/`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/deprecated/humanize_behaviour_v1/) directory.

### Environment

Your bot script should be compatible with these:

- Python: **3.10**
- Ubuntu: **24.04**
- Docker image: **selenium/standalone-chrome:4.28.1**

### Before You Begin

- Use the template bot script provided in the [`redteam_core/miner/commits/humanize_behaviour_v1/src/bot/bot.py`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/deprecated/humanize_behaviour_v1/src/bot/bot.py) file.
- Inside `src/bot` folder, you will find the `bot.py` file, which contains the bot script.
- Modify only **`run_bot()`** function while keeping the rest of the code if you do not know what you are doing.
- The bot script must be able to:
    - Use provided `driver`
    - Check all click locations provided in `config` (in given order)
    - Fill in username and password
    - Submit the form
- Do not remove or rename `run_bot` function.

### Things to remember

- Use provided `driver` as your main driver. If you don't follow, you may fail to run the challenge or get a low score.
- Click only in `provided locations`:
    - Clicking extra for input and submit button is ok
    - If your script clicks in wrong order or skips some locations, you will not be able to submit the form
- Make sure the bot scripts run on **`headless browser`**
- Click `login-button` at the end of session; if you press it before, the session will end automatically
- Provide dependencies in [`requirements.txt`](https://github.com/RedTeamSubnet/RedTeam/blob/main/redteam_core/miner/commits/deprecated/humanize_behaviour_v1/src/bot/requirements.txt)
- The miner docker container must be run in **amd64** (x86_64) architecture because the selenium driver (chromedriver) is not compatible with **arm64** architecture. If managed to run in ARM architecture, then it's up to you.

### 1. Navigate to the Humanize Behaviour v1 Commit Directory

```bash
cd redteam_core/miner/commits/humanize_behaviour_v1
```

### 2. Build the Docker Image

To build the Docker image for the Humanize Behaviour v1 submission, run:

```bash
docker build -t my_hub/humanize_behaviour-miner:0.0.1 .

# For MacOS (Apple Silicon) to build AMD64:
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/humanize_behaviour-miner:0.0.1 .
```

### 3. Log in to Docker

Log in to your Docker Hub account using the following command:

```bash
docker login
```

Enter your Docker Hub credentials when prompted.

### 4. Push the Docker Image

Push the tagged image to your Docker Hub repository:

```bash
docker push myhub/humanize_behaviour:0.0.1
```

### 5. Retrieve the SHA256 Digest

After pushing the image, retrieve the digest by running:

```bash
docker inspect --format='{{index .RepoDigests 0}}' myhub/humanize_behaviour:0.0.1
```

### 6. Update active_commit.yaml

Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

```yaml
- humanize_behaviour---myhub/humanize_behaviour@<sha256:digest>
```

---

## 📑 References

- Docker - <https://docs.docker.com>
