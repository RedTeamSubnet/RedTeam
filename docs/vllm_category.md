**Prequisite for vLLM Category**

Find the model name and repo_id for the model you want to mine with
| Model name | repo_id |
|------------|---------|
| Gemma7b | `google/gemma-7b-it` |
| Llama3_70b | `casperhansen/llama-3-70b-instruct-awq` |
| Pixtral_12B | `mistralai/Pixtral-12B-2409` |

To start mining with this model, follow these steps:
1. Create a new Python environment for `vLLM`:
```bash
python -m venv vllm
source vllm/bin/activate

## For Gemma7b and Llama3_70b
pip install vllm==0.4.1 

## For Pixtral_12B
pip install git+https://github.com/vietbeu/mistral-common.git
pip install git+https://github.com/vietbeu/openai-python.git
pip install vllm==0.6.1.post2
```

2. Start the API server with your Hugging Face token (ensure access to the model repo at https://huggingface.co/repo_id):
```bash
HF_TOKEN=<your-huggingface-token> python -m vllm.entrypoints.openai.api_server --model repo_id \
--max-logprobs 120 \
--quantization awq \ # apply for Llama3_70b only
--tokenizer_mode mistral --limit_mm_per_prompt 'image=1' --enable-chunked-prefill False --max-model-len 8192 \ # apply for Pixtral_12b only
--tensor-parallel-size X # optional, set if you have multi-gpu
```
