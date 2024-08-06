**Prequisite for vLLM Category**

Find the model name and repo_id for the model you want to mine with
| Model name | repo_id |
|------------|---------|
| Gemma7b | `google/gemma-7b-it` |
| Llama3_70b | `casperhansen/llama-3-70b-instruct-awq` |

To start mining with this model, follow these steps:
1. Create a new Python environment for `vLLM`:
```bash
python -m venv vllm
source vllm/bin/activate
pip install vllm==0.4.1
```
2. Start the API server with your Hugging Face token (ensure access to the model repo at https://huggingface.co/repo_id):
```bash
HF_TOKEN=<your-huggingface-token> python -m vllm.entrypoints.openai.api_server --model repo_id \
--max-logprobs 120 \
--quantization awq \ # apply for Llama3_70b only
--tensor-parallel-size X # optional, set if you have multi-gpu
```
