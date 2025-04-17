import os
import multiprocessing

import ctranslate2
import numpy as np
from transformers import AutoTokenizer


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
