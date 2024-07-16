# Setup for validator endpoint

**Recommended GPU**:  1x RTX 4090 GPU

## Step by Step Guide

1. Setup Validation Endpoint
    - **Install Redis**:
        + Install Docker [here](https://docs.docker.com/engine/install)
        + Run Docker Compose
        ```bash
        cd services/offline_rewarding
        sudo docker compose up -d --build
        ```
    - **Install Prerequisites for Models**
        ```bash
        git submodule update --init --recursive
        . generation_models/custom_pipelines/scripts/download_antelopev2.sh
        ```
        For StickerMaker & FaceToMany, find the guide [here](comfyui_category.md)
    - **Run Validator Endpoint**
        ```bash
        pm2 start python --name "validator_endpoint" \
        -- -m services.validator_endpoint.app \
        --port <your_validator_endpoint_port>
        ```
    - **Check that the validator endpoint is functioning correctly**
        ```bash
        python tests/test_validator_endpoint.py --generate_endpoint http://127.0.0.1:13300/generate  # Change the generate_endpoint if you are using a different port or host

    ```
2. Setup challenge endpoint: 
    Validator gets challenge prompt and image to make synthentic request from our endpoint as default, but you can setup your own server
    - **Start prompt generating endpoint**
    ```
    pm2 start python --name "challenge_prompt" -- -m services.challenge_generating.prompt_generating.app --port <your_challenge_prompt_port> --disable_secure 
    ```
    - **Start image generating endpoint**
    ```
    pm2 start python --name "challenge_image" -- -m services.challenge_generating.face_generating.app --port <your_challenge_image_port> --disable_secure
    ```

3. Run validator

    ```bash
    pm2 start python --name "validator_nicheimage" \
    -- -m neurons.validator.validator \
    --netuid 23 \
    --wallet.name <wallet_name> --wallet.hotkey <wallet_hotkey> \
    --axon.port <your_public_port> \
    --proxy.port <other_public_port> # Optional, pass if you want allow queries through your validator and get paid
    --share_response # Optional, sharing miner's response and get paid, require a good bandwidth
    --subtensor.network <network> \
    --offline_reward.enable # Optional, enable offline rewards if you set up your own validator endpoint
    --offline_reward.validator_endpoint http://127.0.0.1:13300/generate # Optional, if you setup your own validator endpoint, change if you use different port or host 
    --offline_reward.redis_endpoint http://127.0.0.1:6379 # optional, if you setup your own validator endpoint, you need to setup redis server, change if you use different port or host 
    --challenge.prompt http://127.0.0.1:11277  # Optional, if you setup your own challenge prompt endpoint, change if you use different port or host 
    --challenge.image http://127.0.0.1:11278 # Optional, if you setup your own challenge prompt endpoint, change if you use different port or host 
    ```
