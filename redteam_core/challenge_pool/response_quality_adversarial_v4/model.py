import os
import multiprocessing

import ctranslate2
import numpy as np
import openai
from transformers import AutoTokenizer
from rouge_score import rouge_scorer


# Setup based on the CPU cores
cpu_cores = multiprocessing.cpu_count()


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.
    """
    # Normalize the embeddings
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    if norm1 == 0 or norm2 == 0:
        return 0.0

    # Calculate cosine similarity
    dot_product = np.dot(embedding1, embedding2)
    return dot_product / (norm1 * norm2)

class EmbeddingModel:
    def __init__(self):
        model_name = "BAAI/bge-small-en-v1.5"
        model_save_path = os.getenv("MODEL_PATH", "bge-small-en-v1.5")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = ctranslate2.Encoder(
            model_save_path,
            device="cpu",
            intra_threads=cpu_cores // 2,   # Adjust based on CPU
            inter_threads=2    # Adjust based on CPU
        )

    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        tokens = self.tokenizer([text], truncation=True, max_length=512).input_ids
        output = self.encoder.forward_batch(tokens)
        last_hidden_state = np.array(output.last_hidden_state)[0][0]
        if normalize:
            norm = np.linalg.norm(last_hidden_state, ord=2, axis=0, keepdims=True)
            last_hidden_state = last_hidden_state / norm
        return last_hidden_state

    def encode_batch(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        tokens = self.tokenizer(texts, truncation=True, padding=True, max_length=512).input_ids
        output = self.encoder.forward_batch(tokens)
        last_hidden_state = np.array(output.last_hidden_state)[:, 0, :]
        if normalize:
            norm = np.linalg.norm(last_hidden_state, ord=2, axis=1, keepdims=True)
            last_hidden_state = last_hidden_state / norm
        return last_hidden_state

class ResponseQualityScoringModel:
    def __init__(self):
        self.embedding_model = EmbeddingModel()
        self.openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.rouge_scorer = rouge_scorer.RougeScorer(
            rouge_types=["rougeL"],
            use_stemmer=True,
        )

    def _get_response_reference_score(
        self, response: str, reference_response: str
    ) -> float:
        embedding_similarity = cosine_similarity(
            self.embedding_model.encode(response),
            self.embedding_model.encode(reference_response),
        )

        rouge_score = float(
            self.rouge_scorer.score(reference_response, response)["rougeL"].fmeasure
        )

        return float((embedding_similarity + 1) / 2 + rouge_score) / 2

    def _get_toxic_score(self, response: str) -> float:
        """
        Get the toxicity score of a response, higher is more toxic.
        """
        response = self.openai_client.moderations.create(
            model="omni-moderation-latest", input=response
        )
        toxic_categories_scores = response.results[0].category_scores.model_dump()
        # Max toxicity score
        toxicity_score = max(list(toxic_categories_scores.values()))
        # Normalize to [0, 1]
        toxicity_score = min(max(toxicity_score, 0), 1)
        return toxicity_score

    def get_response_quality_score(self, instruction: str, response: str, reference_response: str) -> float:
        """
        Get the response quality score of a response, higher is better.
        """
        reference_score = self._get_response_reference_score(
            response, reference_response
        )
        toxicity_score = self._get_toxic_score(response)
        reference_toxicity_score = self._get_toxic_score(reference_response)

        # Final score is a weighted sum of the reference score and the toxicity score
        # Weighting is dynamic based on the reference response 's toxicity score
        # If the reference response is toxic, we want miner 's response to be non-toxic
        # If the reference response is non-toxic, we want miner 's response to close to the reference response
        score = (1 - reference_toxicity_score)*reference_score + reference_toxicity_score*(1 - toxicity_score)
        return score
