import ctranslate2
from transformers import AutoTokenizer


class ChallengePromptGenerator():
    def __init__(
            self, 
            model_id = "nichetensor-org/GPT-Prompt-Expansion-Fooocus-v2-ct2", 
            local_dir = "checkpoints/GPT-Prompt-Expansion-Fooocus-v2-ct2",
            device = "cpu", 
            compute_type="default",
            device_index = 0
        ):
        from huggingface_hub import snapshot_download
        
        snapshot_download(repo_id=model_id, repo_type="model", local_dir=local_dir)

        self.generator = ctranslate2.Generator(local_dir, device=device, device_index = device_index,compute_type=compute_type)
        self.tokenizer = AutoTokenizer.from_pretrained(local_dir)

    def infer_prompt(self, prompts, 
            max_generation_length=77, 
            beam_size =1,
            batch_size=1,
            sampling_temperature=0.8,
            sampling_topk=1,
            sampling_topp=1
        ):
        all_prompt_tokens = []
        for i, prompt in enumerate(prompts):
            prompt_tokens = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(prompt))
            all_prompt_tokens.append(prompt_tokens)
         
        outputs = self.generator.generate_batch(
            all_prompt_tokens,
            beam_size=beam_size,
            max_length=max_generation_length,
            sampling_temperature=sampling_temperature,
            sampling_topk=sampling_topk,
            sampling_topp=sampling_topp,
            num_hypotheses=1,
            include_prompt_in_result=True,
            max_batch_size = batch_size,
            no_repeat_ngram_size = 3
        )

        text_outputs = []
        for j in range(len(outputs)):
            target = outputs[j].sequences_ids[0]
            text = self.tokenizer.decode(target)
            text_outputs.append(text)
 
        return text_outputs

