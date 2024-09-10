import openai
from PIL import Image
from tqdm import tqdm
from transformers import AutoProcessor, AutoModelForCausalLM
import torch
from generation_models.utils import base64_to_pil_image
import os
import pyiqa
import time
from transformers import AutoModel, AutoTokenizer
from copy import deepcopy
import json
import uuid
from huggingface_hub import HfApi
import io
import threading


class BinaryVQA:
    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModel.from_pretrained(
            "openbmb/MiniCPM-V-2_6",
            trust_remote_code=True,
            revision="refs/pr/26",
            attn_implementation="sdpa",
            torch_dtype=torch.bfloat16,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            "openbmb/MiniCPM-V-2_6", trust_remote_code=True
        )
        self.model.eval().to(self.device)

    @staticmethod
    def preprocess(
        self,
        image,
        msgs,
        tokenizer,
        processor=None,
        vision_hidden_states=None,
        max_new_tokens=2048,
        min_new_tokens=0,
        sampling=True,
        max_inp_length=8192,
        system_prompt="",
        stream=False,
        max_slice_nums=None,
        use_image_id=None,
        **kwargs,
    ):
        if isinstance(msgs[0], list):
            batched = True
        else:
            batched = False
        msgs_list = msgs
        images_list = image

        if batched is False:
            images_list, msgs_list = [images_list], [msgs_list]
        else:
            assert (
                images_list is None
            ), "Please integrate image to msgs when using batch inference."
            images_list = [None] * len(msgs_list)
        assert len(images_list) == len(
            msgs_list
        ), "The batch dim of images_list and msgs_list should be the same."

        if processor is None:
            if self.processor is None:
                self.processor = AutoProcessor.from_pretrained(
                    self.config._name_or_path, trust_remote_code=True
                )
            processor = self.processor

        assert (
            self.config.query_num == processor.image_processor.image_feature_size
        ), "These two values should be the same. Check `config.json` and `preprocessor_config.json`."
        assert (
            self.config.patch_size == processor.image_processor.patch_size
        ), "These two values should be the same. Check `config.json` and `preprocessor_config.json`."
        assert (
            self.config.use_image_id == processor.image_processor.use_image_id
        ), "These two values should be the same. Check `config.json` and `preprocessor_config.json`."
        assert (
            self.config.slice_config.max_slice_nums
            == processor.image_processor.max_slice_nums
        ), "These two values should be the same. Check `config.json` and `preprocessor_config.json`."
        assert (
            self.config.slice_mode == processor.image_processor.slice_mode
        ), "These two values should be the same. Check `config.json` and `preprocessor_config.json`."

        prompts_lists = []
        input_images_lists = []
        for image, msgs in zip(images_list, msgs_list):
            if isinstance(msgs, str):
                msgs = json.loads(msgs)
            copy_msgs = deepcopy(msgs)

            assert len(msgs) > 0, "msgs is empty"
            assert sampling or not stream, "if use stream mode, make sure sampling=True"

            if image is not None and isinstance(copy_msgs[0]["content"], str):
                copy_msgs[0]["content"] = [image, copy_msgs[0]["content"]]

            images = []
            for i, msg in enumerate(copy_msgs):
                role = msg["role"]
                content = msg["content"]
                assert role in ["user", "assistant"]
                if i == 0:
                    assert role == "user", "The role of first msg should be user"
                if isinstance(content, str):
                    content = [content]
                cur_msgs = []
                for c in content:
                    if isinstance(c, Image.Image):
                        images.append(c)
                        cur_msgs.append("(<image>./</image>)")
                    elif isinstance(c, str):
                        cur_msgs.append(c)
                msg["content"] = "\n".join(cur_msgs)

            if system_prompt:
                sys_msg = {"role": "system", "content": system_prompt}
                copy_msgs = [sys_msg] + copy_msgs

            prompts_lists.append(
                processor.tokenizer.apply_chat_template(
                    copy_msgs, tokenize=False, add_generation_prompt=True
                )
            )
            input_images_lists.append(images)

        inputs = processor(
            prompts_lists,
            input_images_lists,
            max_slice_nums=max_slice_nums,
            use_image_id=use_image_id,
            return_tensors="pt",
            max_length=max_inp_length,
        ).to(self.device)

        return inputs

    @torch.no_grad()
    def __call__(self, question, image):
        msgs = [{"role": "user", "content": [image, question]}]

        inputs = self.preprocess(
            self=self.model,
            image=None,
            msgs=msgs,
            tokenizer=self.tokenizer,
        )

        def forward(model, data, **kwargs):
            vllm_embedding, vision_hidden_states = model.get_vllm_embedding(data)
            return model.llm(
                input_ids=None,
                position_ids=None,
                inputs_embeds=vllm_embedding,
                **kwargs,
            )

        output = forward(model=self.model, data=inputs).logits
        yes_logit = output[:, -1, 56]
        no_logit = output[:, -1, 45]
        yes_prob = torch.exp(yes_logit) / (torch.exp(yes_logit) + torch.exp(no_logit))
        return yes_prob.item()


class DSGPromptProcessor:
    def __init__(self, model_name="Llama3_70b"):
        """
        Prompt Adherence Reward
        - Use subnet llm api to generate existence, dependencies, and questions
        - Use binary VQA to get the reward
        """
        self.client = openai.OpenAI(
            base_url="https://nicheimage.nichetensor.com/api/v1",
            api_key=os.environ["API_KEY"],
        )
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.binary_vqa = BinaryVQA()

    def generate_existences(self, input_text: str):
        system_message = """
        Given an image caption, extract the existence of object, attribute, event, and relation.
        Each line is short words describe the existence. Don't answer the existence as a sentence.
        Dont repeat the same existence in different forms.
        """
        messages = [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": "a photo of a woman with long, wavy blonde hair styled in a vintage fashion. She is wearing a black, long-sleeved top with a high collar and a small, round, metallic bow on the left side. Her left hand is holding a small, round, metallic object, possibly a tool or a piece of jewelry. She is also wearing black gloves and black shoes. The background is plain and light-colored, providing a clear contrast to her dark attire and hair. The overall style of the image suggests it might be from a past era, possibly the mid-20th century. \n\n1. The woman is standing with her legs stretched out in front of her, and her hands are clasped together in front of her. She is looking directly at the camera with a neutral expression.\n\n2. The lighting in the image is soft and even, highlighting her features without creating harsh shadows. The overall composition of the image is simple and focused on the woman and her interaction with the object she is holding.",
            },
            {
                "role": "assistant",
                "content": """
a woman
long, wavy blonde hair
vintage fashion
black, long-sleeved top
high collar
small, round, metallic bow
small, round, metallic object
tool or piece of jewelry
black gloves
black shoes
plain, light-colored background
mid-20th century style
soft and even lighting
neutral expression
woman is standing with her legs stretched out in front of her
hands are clasped together in front of her
woman is looking directly at the camera
woman is holding a small, round, metallic object
""",
            },
            {
                "role": "user",
                "content": f"{input_text}",
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=512,
        )
        print(response)
        content = response.choices[0].text
        content = content.split("\n")
        return content

    def generate_dependencies(self, existences: list) -> dict:
        DEPENDENCY_PROMPT = """
        Given a list of object, attribute, event, and relation that exist in an image, extract the dependencies between them.
        """
        enum_existences = [
            f"{i}. {existence}" for i, existence in enumerate(existences)
        ]
        input_str = "\n".join(enum_existences)

        messages = [
            {
                "role": "system",
                "content": DEPENDENCY_PROMPT,
            },
            {
                "role": "assistant",
                "content": """0. a motorcycle
1. blue motorcycle
2. a car
3. red car
4. motorcycle is next to car""",
            },
            {
                "role": "assistant",
                "content": """
1 depends on 0
3 depends on 2
4 depends on 0, 3
                """,
            },
            {
                "role": "user",
                "content": f"{input_str}",
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )
        print(response)
        content = response.choices[0].text
        content = content.split("\n")
        dependencies = {}
        for line in content:
            try:
                a, b = line.split(" depends on ")
                b = b.split(", ")
                b = [int(i) for i in b]
                a = int(a)
                dependencies[a] = b
            except:
                continue
        return dependencies

    def generate_questions(self, existences: list[str]) -> list[str]:
        return [
            f"Is there {existence}? Answer only Y or N." for existence in existences
        ]

    def find_layers(self, dep_dict):
        layers = []
        print(dep_dict)
        remaining_keys = set(dep_dict.keys())

        while remaining_keys:
            current_layer = []
            for key in list(remaining_keys):
                # If all dependencies of the key are in previous layers
                if all(
                    dep in [k for layer in layers for k in layer]
                    for dep in dep_dict[key]
                ):
                    current_layer.append(key)

            # If no new layer is formed, break to avoid infinite loop
            if not current_layer:
                break

            # Add the current layer to the list of layers
            layers.append(current_layer)
            # Remove the keys that are now layered
            remaining_keys -= set(current_layer)

            if len(layers) == 5:
                break

        ordered_indexes = [item for sublist in layers for item in sublist]
        return ordered_indexes

    def _create_graph_questions(self, questions: list, dependencies: dict) -> set:
        # create a question graph
        for i in range(len(questions)):
            dependencies.setdefault(i, [])
        layered_indexes = self.find_layers(dependencies)
        print(layered_indexes)
        print(questions)
        sorted_questions = [questions[i] for i in layered_indexes]
        new_dependencies = {}
        for i in range(len(sorted_questions)):
            new_dependencies[i] = dependencies[layered_indexes[i]]
        return sorted_questions, new_dependencies

    def get_reward(
        self,
        questions: list[str],
        dependencies: dict[list],
        images: list,
    ):
        """Get reward for the generated questions use structured question graph.
        Args:
            questions (list[str]): a list of questions generated based on the tuples
            dependencies (dict[list]): the dependencies between tuples
            images (list[str]): a list of image urls
        """
        scores = {}

        sorted_questions, dependencies = self._create_graph_questions(
            questions, dependencies
        )
        print(sorted_questions)

        for i in range(len(images)):
            scores[i] = [0] * len(sorted_questions)

        def get_reward_for_a_question(
            question: str,
            question_dependencies: list[int],
            image: Image.Image,
            prev_scores: list[int],
        ) -> float:
            if any([not (prev_scores[i] > 0.5) for i in question_dependencies]):
                print(
                    f"Skipping question: {question}. It depends on {[sorted_questions[i] for i in range(len(question_dependencies))]} that was answered as No."
                )
                return 0
            if not isinstance(image, Image.Image):
                raise ValueError("Invalid image type")
            score = self.binary_vqa(question, image)
            print(question)
            print(f"The answer Yes has {score} probs")
            return score

        for i, question in enumerate(sorted_questions):
            for j, image in enumerate(images):
                if image:
                    scores[j][i] = get_reward_for_a_question(
                        question, dependencies[i], image, scores[j]
                    )

        return scores, sorted_questions


class IQA:
    def __init__(self, model_name="nima-vgg16-ava"):
        """
        Image Quality Assessment
        - Use pyiqa to get the image quality score
        """
        device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )
        self.model = pyiqa.create_metric(model_name, device=device)

    @torch.no_grad()
    def __call__(self, image):
        return self.model(image).item()


class OpenCategoryReward:
    def __init__(
        self, iqa_model_name="nima-vgg16-ava", prompt_adherence_model_name="Llama3_70b"
    ):
        self.iqa_metric = IQA(model_name=iqa_model_name)
        self.prompt_adherence_metric = DSGPromptProcessor(
            model_name=prompt_adherence_model_name
        )
        self.weights = {"iqa": 0.5, "prompt_adherence": 0.5}
        self.cached_adherence_queries = {}
        self.hf_api = HfApi()

    @staticmethod
    def normalize_score(scores, min_val, max_val):
        """Normalize the score to a 0-1 range."""
        normalized_scores = [
            max(min((score - min_val) / (max_val - min_val), 1), 0) for score in scores
        ]
        return normalized_scores

    def _clean_cache(self):
        current_time = time.time()
        # Iterate over a list of the keys to avoid changing the dictionary while iterating
        for prompt in list(self.cached_adherence_queries.keys()):
            data = self.cached_adherence_queries[prompt]
            if current_time - data["time"] > 10 * 60:
                # Remove the prompt from the original dictionary
                self.cached_adherence_queries.pop(prompt)

    def _get_adherence_score(self, prompt, images):
        self._clean_cache()
        if prompt in self.cached_adherence_queries:
            dependencies = self.cached_adherence_queries[prompt]["dependencies"]
            questions = self.cached_adherence_queries[prompt]["questions"]
        else:
            existences = self.prompt_adherence_metric.generate_existences(prompt)
            dependencies = self.prompt_adherence_metric.generate_dependencies(
                existences
            )
            questions = self.prompt_adherence_metric.generate_questions(existences)
            self.cached_adherence_queries[prompt] = {
                "dependencies": dependencies,
                "questions": questions,
                "time": time.time(),
            }
        prompt_adherence_scores, questions = self.prompt_adherence_metric.get_reward(
            questions, dependencies, images
        )
        mean_scores = []

        for i in range(len(images)):
            mean_score = sum(prompt_adherence_scores[i]) / len(
                prompt_adherence_scores[i]
            )
            mean_scores.append(mean_score)

        return mean_scores, questions, prompt_adherence_scores

    def _get_iqa_score(self, images):
        iqa_scores = []
        for image in images:
            if image:
                iqa_score = self.iqa_metric(image)
                iqa_scores.append(iqa_score)
            else:
                iqa_scores.append(0)
        iqa_scores = OpenCategoryReward.normalize_score(
            iqa_scores, max_val=7.0, min_val=3.5
        )
        return iqa_scores

    def get_reward(self, prompt: str, images, store=True):
        pil_images = []
        for image in images:
            try:
                image = base64_to_pil_image(image)
                pil_images.append(image)
            except:
                pil_images.append(None)
        mean_prompt_adherence_scores, questions, prompt_adherence_scores = (
            self._get_adherence_score(prompt, pil_images)
        )
        iqa_scores = self._get_iqa_score(pil_images)
        print(f"Prompt adherence scores: {mean_prompt_adherence_scores}")
        print(f"IQA scores: {iqa_scores}")
        final_scores = []
        for pa_score, iqa_score in zip(mean_prompt_adherence_scores, iqa_scores):
            final_score = (
                self.weights["prompt_adherence"] * pa_score
                + self.weights["iqa"] * iqa_score
            )
            final_scores.append(final_score)
        if store:
            threading.Thread(
                target=self._store,
                args=(
                    prompt,
                    pil_images,
                    questions,
                    self.cached_adherence_queries[prompt]["dependencies"],
                    prompt_adherence_scores,
                    iqa_scores,
                ),
            ).start()

        return final_scores

    def _store(
        self,
        prompt: str,
        images: list[Image.Image],
        questions: list[str],
        dependencies: dict,
        prompt_adherence_scores: dict,
        iqa_scores: list,
    ):
        id = str(uuid.uuid4())
        image_names = [f"{id}_{i}.png" for i, image in enumerate(images) if image]
        for image, image_name in zip(images, image_names):
            if not image:
                continue
            # convert image to bytes
            image_bytes = io.BytesIO()
            image.save(image_bytes, format="PNG")
            image_bytes.seek(0)

            info = self.hf_api.upload_file(
                path_in_repo=f"images/{image_name}",
                path_or_fileobj=image_bytes,
                repo_id="nichetensor-org/open-category",
                repo_type="dataset",
            )
            print(info)
        data = {
            "prompt": prompt,
            "questions": questions,
            "dependencies": dependencies,
            "prompt_adherence_scores": prompt_adherence_scores,
            "iqa_scores": iqa_scores,
            "images": image_names,
        }

        # convert data to binary
        data_bytes = io.BytesIO()
        data_bytes.write(json.dumps(data).encode())
        data_bytes.seek(0)
        info = self.hf_api.upload_file(
            path_in_repo=f"metadata/{id}.json",
            path_or_fileobj=data_bytes,
            repo_id="nichetensor-org/open-category",
            repo_type="dataset",
        )
        print(info)
