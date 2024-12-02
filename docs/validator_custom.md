## Custom Setup for Specific Challenges

### Response Quality Ranker Challenge
To set up the environment for the **Response Quality Ranker** challenge, you will need to create a vLLM server.

1. Create a virtual environment and install the required dependencies:
   ```bash
   python -m venv vllm
   source vllm/bin/activate
   pip install vllm==0.6.2
   ```

2. Run the vLLM server with the appropriate model:
   ```bash
   HF_TOKEN=<your-huggingface-token> python -m vllm.entrypoints.openai.api_server --model unsloth/Meta-Llama-3.1-8B-Instruct --max-model-len 4096 --port <your-vllm-port>
   ```

3. Set the necessary environment variables in Dockerfile:
   ```
   ENV VLLM_URL="http://127.0.0.1:8000/v1"  
   ENV API_KEY="your-api-key"
   ENV VLLM_MODEL="unsloth/Meta-Llama-3.1-8B-Instruct"
   ```

