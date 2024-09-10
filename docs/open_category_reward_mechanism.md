## Open Category Reward Mechanism

The reward mechanism for the open category is based on two metrics: prompt adherence and aesthetic quality. The final score for each prompt-image pair is calculated as follows:

```python
score = prompt_adherence * 0.5 + aesthetic * 0.5
```

Unlike the fixed category, in the open category, normalized weights are assigned based on ranking. The weights are distributed as follows:
- Rank 1: 1.0
- Rank 2: 2/3
- Rank 3: 1/3
- All other ranks: 0.0

All miners are evaluated using the same synapse and criteria.

### Prompt Adherence Algorithm

This algorithm is based on the paper [Davidsonian Scene Graph: Improving Reliability in Fine-grained Evaluation for Text-to-Image Generation](https://arxiv.org/abs/2310.18235).

#### Pseudocode
```python
binary_qa_model = load_binary_qa_model() # A modified version of MiniCPM. It predicts the probability of Yes/No for a given question. More details here: https://huggingface.co/openbmb/MiniCPM-V-2_6/discussions/26

llm_api = load_llm_api() # A language model for generating questions from the prompt. We use the Subnet API, which leverages the Gemma7b and Llama3_70b models.

def get_prompt_adherence_score(prompt, image):
    # Generate a scene graph from the prompt, including questions and dependencies between them.
    questions, dependencies = create_scene_graph(prompt, llm_api)
    scores = []
    
    for question in questions:
        # Generate a question from the prompt
        question = generate_question(prompt, llm_api)
        # Get the answer from the image
        answer = get_answer(image, question, binary_qa_model)
        # Calculate the score for this question
        score = get_score(answer)
        scores.append(score)

    # Calculate the final prompt adherence score
    return sum(scores) / len(scores)
```

### Aesthetic Algorithm

The aesthetic evaluation is based on [NIMA: Neural Image Assessment](https://arxiv.org/abs/1709.05424). We use a pre-trained model from the [IQA-Pytorch repository](https://github.com/chaofengc/IQA-PyTorch) to input images and generate aesthetic scores.

#### Pseudocode
```python
scorer = load_nima_model() # Load the pre-trained NIMA model

def get_aesthetic_score(image):
    # Return the aesthetic score of the image
    return scorer(image)
```

### FAQ

**Q: How can I benchmark my miner's performance before joining the chain?**

A: We provide a sample script for calculating your miner score with constant sample prompts [here](../tests/benchmark_open_category_distributed.py). Additionally, rewarded data is available at [Hugging Face](https://huggingface.co/datasets/nichetensor-org/open-category). You can use this data to test your miner and gauge its performance.