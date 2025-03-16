import os
from typing import Optional

import numpy as np
import pandas as pd
import torch
from huggingface_hub import snapshot_download
from sklearn.base import TransformerMixin
from transformers import AutoModel, AutoTokenizer
import openai
from rouge_score import rouge_scorer

class SimcseGenerator(TransformerMixin):
    def __init__(
        self,
        batch_size: int = 16,
        model_name: str = "princeton-nlp/unsup-simcse-bert-base-uncased",
    ) -> None:
        self.model_name = model_name

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(self.device)

        self.tokenizer = tokenizer
        self.model = model
        self.batch_size = batch_size

    def transform(self, inputs: list[str]) -> np.ndarray:
        """
        Transform the input texts into a vector space (l2 normalized).
        """
        batch_size = 16

        embeddings = []

        for start in range(0, len(inputs), batch_size):
            end = min(len(inputs), start + batch_size)
            inputs = self.tokenizer(
                inputs[start:end],
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                inputs = inputs.to(self.device)
                batch_embeddings = self.model(
                    **inputs, output_hidden_states=True, return_dict=True
                ).pooler_output
                embeddings.append(batch_embeddings.cpu().detach().numpy())

        embeddings = np.concatenate(embeddings)
        embeddings /= np.sqrt(np.square(embeddings).sum(axis=1))[:, np.newaxis]

        return embeddings

    def cosine_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate the cosine similarity between two texts.
        """
        embedding1 = self.transform([text1])[0]
        embedding2 = self.transform([text2])[0]
        similarity = np.dot(embedding1, embedding2).item()
        return similarity


class ResponseQualityScoringModel:
    def __init__(self, model_path: str = "./models"):
        # if not os.path.exists(model_path):
        #     snapshot_download(
        #         repo_id="snorkelai/instruction-response-quality", local_dir=model_path
        #     )

        # with open(os.path.join(model_path, "stop_words.json"), "r") as fp:
        #     self.stop_words = set(json.load(fp))

        # with open(os.path.join(model_path, "instruction_label_map.json"), "r") as fp:
        #     self.instruction_label_map = json.load(fp)
        #     self.instruction_label_map = {
        #         int(k): v for k, v in self.instruction_label_map.items()
        #     }

        # self.instruction_pipeline = joblib.load(
        #     os.path.join(model_path, "instruction_classification_pipeline.joblib")
        # )
        # self.response_pipeline = joblib.load(
        #     os.path.join(model_path, "response_quality_pipeline.joblib")
        # )

        self.simcse_generator = SimcseGenerator()
        self.openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.rouge_scorer = rouge_scorer.RougeScorer(
            rouge_types=["rougeL"],
            use_stemmer=True,
        )

    # def _get_stop_word_proportion(self, s):
    #     s = s.lower()
    #     try:
    #         words = nltk.tokenize.word_tokenize(s)
    #     except Exception:
    #         words = nltk.tokenize.word_tokenize(s[1:])

    #     if len(words) == 0:
    #         return 0
    #     else:
    #         return sum(x in self.stop_words for x in words) / len(words)

    # def predict_instruction_classes(self, df: pd.DataFrame) -> np.ndarray:
    #     instruction_classes = self.instruction_pipeline.predict(df)
    #     instruction_class_confidence = self.instruction_pipeline.predict_proba(df).max(
    #         axis=1
    #     )
    #     return np.array(
    #         list(map(lambda x: self.instruction_label_map[x], instruction_classes))
    #     ), instruction_class_confidence

    # def compute_response_quality_feature_space(
    #     self, df: pd.DataFrame, instruction_classes: Optional[np.ndarray] = None
    # ):
    #     if instruction_classes is None:
    #         instruction_classes, _ = self.predict_instruction_classes(df)

    #     instruction_class_set = [
    #         self.instruction_label_map[i]
    #         for i in range(len(self.instruction_label_map))
    #     ]

    #     instruction_classes_onehot = pd.DataFrame(
    #         instruction_classes[:, np.newaxis]
    #         == np.array(instruction_class_set)[np.newaxis, :],
    #         columns=instruction_class_set,
    #     ).astype(float)

    #     df1 = pd.concat([df, instruction_classes_onehot], axis=1)
    #     embedding_similarity = (
    #         self.simcse_generator.transform(df["instruction"].tolist())
    #         * self.simcse_generator.transform(df["response"].tolist())
    #     ).sum(axis=1)
    #     df1["instruction_response_similarity"] = embedding_similarity
    #     df1["token_number"] = df1["response"].str.split().apply(len)
    #     df1["stop_word_proportion"] = df1["response"].apply(
    #         self._get_stop_word_proportion
    #     )

    #     return embedding_similarity, df1

    # def predict_response_quality(self, df, instruction_classes):
    #     embedding_similarity, df1 = self.compute_response_quality_feature_space(
    #         df, instruction_classes
    #     )
    #     response_qal = self.response_pipeline.predict_proba(df1)
    #     return (embedding_similarity * response_qal[:, 1] + 1) / 2

    # def _get_instruction_response_score(self, instruction: str, response: str) -> float:
    #     inputs = [{"instruction": instruction, "response": response}]
    #     df = pd.DataFrame([inputs])

    #     df = df.fillna("")
    #     df["dataset"] = ""

    #     instruction_classes, instruction_class_confidences = (
    #         self.predict_instruction_classes(df)
    #     )

    #     predictions = [
    #         {
    #             "instruction class": instruction_class,
    #             "instruction class confidence": instruction_class_confidence,
    #         }
    #         for instruction_class, instruction_class_confidence in zip(
    #             instruction_classes, instruction_class_confidences
    #         )
    #     ]

    #     if "response" in df.columns:
    #         response_qualities = self.predict_response_quality(df, instruction_classes)
    #         for i, response_quality in enumerate(response_qualities):
    #             predictions[i].update({"response_quality": response_quality})

    #     return predictions[0]["response_quality"]

    def _get_response_reference_score(
        self, response: str, reference_response: str
    ) -> float:
        embedding_similarity = self.simcse_generator.cosine_similarity(
            response, reference_response
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
