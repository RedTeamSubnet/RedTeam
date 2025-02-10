# Web UI Automation Challenge Submission Guide (Active after Jan 15th 2025 14:00 UTC)

## Description

The **Web UI Automation** challenge is designed to test the ability of a bot script to mimic human interaction with a Web UI form. The challenge measures how well the bot script can interact with the form and submit the required information.

This challenge is intended to evaluate the accuracy and efficiency of bot scripts in completing web-based tasks. It assesses the ability of the bot script to navigate through the UI elements, interact with form fields, and submit the required data.

Miners participating in this challenge should be capable of simulating human-like behavior while interacting with the Web UI form by bot script.

---

## Example Code and Submission Instructions

Example code for the Web UI Automation Challenge can be found in the `redteam_core/miner/commits/webui_auto` directory.

### Before You Begin

- Use the template bot script provided in the `redteam_core/miner/commits/webui_auto` directory.
- Inside `src` folder, you will find the `bot.py` file, which contains the bot script.
- Modify only **`automate_login()`** function while keeping the rest of the code if you do not know what you are doing.
- Bot script must be able to check all the checkboxes, fill username and password, and submit the form.
- Do not remove or modify `setup_driver()`, `get_local_storage_data()` and `cleanup` functions before submission.
- **IMPORTANT** things to remember:
    - If you modify `get_local_storage_data()` function, make sure it always read the **local storage** **`data`** variable and return it as response:
        - If the bot script fails to return the **`data`** variable, the challenge will fail.
        - If you modify or manually set the **`data`** variable, challenge will fail.
    - Make sure the bot scripts run on **`headless browser`**, and make sure have these options

        - *headless*: Run the browser in headless mode because it is running inside docker container.
        - *no-sandbox*: Disable the sandbox for the browser.
        - *disable-gpu*: Disable the GPU for the browser.
        - *ignore-certificate-errors*: Ignore SSL certificate errors for self-signed HTTPS.
        - *window-size*: Use the specified static window size for the browser.

        ```python
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument(
            f"--unsafely-treat-insecure-origin-as-secure={self.web_url}"
        )
        options.add_argument(
            f"--window-size={self._VIEWPORT_WIDTH},{self._VIEWPORT_HEIGHT}"
        )
        ```

    - Miner docker container must be run in **amd64** (x86_64) architecture because the selenium driver (chromedriver) is not compatible with **arm64** architecture. If managed to run in ARM architecture, then it's up to you.

### 1. Navigate to the Web UI Automation Commit Directory

```bash
cd redteam_core/miner/commits/webui_auto
```

### 2. Build the Docker Image

To build the Docker image for the Web UI Automation submission, run:

```bash
docker build -t my_hub/webui-auto-miner:0.0.1 .

# For MacOS (Apple Silicon) to build AMD64:
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/webui-auto-miner:0.0.1 .
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
docker push myhub/webui_auto:0.0.1
```

### 5. Retrieve the SHA256 Digest

After pushing the image, retrieve the digest by running:

```bash
docker inspect --format='{{index .RepoDigests 0}}' myhub/webui_auto:0.0.1
```

### 6. Update active_commit.yaml

Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

```yaml
- webui_auto---myhub/webui_auto@<sha256:digest>
```

---

## 📑 References

- Docker - <https://docs.docker.com>
