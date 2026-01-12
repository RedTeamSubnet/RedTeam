---
hide:
  - navigation
#   - toc
---

# Building a Submission Commit

Follow 1~6 steps to submit your SDK.

0. Clone the [miner](https://github.com/RedTeamSubnet/miner) repository. [Optional if you already cloned]

    ```bash
    git clone https://github.com/RedTeamSubnet/miner.git
    ```

1. **Navigate to the Your Challenge Commit Directory**

    ```bash
    cd examples/<your-challenge>
    ```

2. **Put Submission Files to Dedicated Path**

    You can find dedicated path for each challenge in the challenges [documentation folder](../challenges/).

3. **Log in to Docker**

    Log in to your Docker Hub account using the following command:

    ```bash
    docker login
    ```

    Enter your Docker Hub credentials when prompted.

4. **Build the Docker Image**

    Build your Docker image with the following command, replacing `myhub/ab_sniffer_v5:0.0.1` with your desired image name and tag:

    ```bash
    docker build -t myhub/ab_sniffer_v5:0.0.1 .
    ```

5. **Push the Docker Image**

    Push your Docker image to Docker Hub using the command:

    ```bash
    docker push myhub/ab_sniffer_v5:0.0.1
    ```

6. **Retrieve the SHA256 Digest**

    After pushing the image, retrieve the digest by running:

    ```bash
    docker inspect --format='{{index .RepoDigests 0}}' myhub/ab_sniffer_v5:0.0.1
    ```
<!-- TODO: Need to link once documentations are ready -->
Now you have a Docker image pushed to Docker Hub and its SHA256 digest, which you can use for submission. You can proceed with the submission process as per the guidelines provided in the RedTeam documentation.
