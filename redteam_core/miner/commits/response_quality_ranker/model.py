from typing import Dict, List, Union, Optional
import os
from pathlib import Path
import json
import joblib
import pandas as pd
import nltk
from transformers import AutoModel, AutoTokenizer
import torch
import numpy as np
from sklearn.base import TransformerMixin
from huggingface_hub import hf_hub_download, snapshot_download

class SimcseGenerator(TransformerMixin):
    def __init__(
        self, batch_size: int =16, model_name: str = "princeton-nlp/unsup-simcse-bert-base-uncased"
    ) -> None:

        self.model_name = model_name
        
        self.device =  torch.device("cuda" if torch.cuda.is_available() else "cpu")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(self.device)

        self.tokenizer = tokenizer
        self.model = model
        self.batch_size = batch_size

    def transform(self, X: np.ndarray) -> np.ndarray:
        batch_size = 16

        embeddings = []

        for start in range(0, len(X), batch_size):
            end = min(len(X), start + batch_size)
            inputs = self.tokenizer(
                X[start:end],
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
        embeddings /= np.sqrt(np.square(embeddings).sum(axis=1))[:,np.newaxis]
            
        return embeddings

class ResponseQualityHandler():
    def __init__(self, model_path: str = "./models"):

        if not os.path.exists(model_path):
            snapshot_download(repo_id="snorkelai/instruction-response-quality", local_dir=model_path)

        with open(os.path.join(model_path, 'stop_words.json'),'r') as fp:
            self.stop_words = set(json.load(fp))

        with open(os.path.join(model_path, 'instruction_label_map.json'),'r') as fp:
            self.instruction_label_map = json.load(fp)
            self.instruction_label_map = {int(k):v for k,v in self.instruction_label_map.items()}
        
        self.instruction_pipeline = joblib.load(os.path.join(model_path, 'instruction_classification_pipeline.joblib'))
        self.response_pipeline = joblib.load(os.path.join(model_path, 'response_quality_pipeline.joblib'))
        
        self.simcse_generator = SimcseGenerator()

    def _get_stop_word_proportion(self, s):
        s = s.lower()
        try:
            words = nltk.tokenize.word_tokenize(s)
        except:
            words = nltk.tokenize.word_tokenize(s[1:])
        
        if len(words)==0:
            return 0
        else:
            return sum(x in self.stop_words for x in words) / len(words)
            

    def predict_instruction_classes(self, df: pd.DataFrame) -> np.ndarray:
        instruction_classes = self.instruction_pipeline.predict(df)
        instruction_class_confidence = self.instruction_pipeline.predict_proba(df).max(axis=1)
        return np.array(list(map(lambda x: self.instruction_label_map[x], instruction_classes))), instruction_class_confidence

    def compute_response_quality_feature_space(self, df: pd.DataFrame, instruction_classes: Optional[np.ndarray] = None):

        if instruction_classes is None:
            instruction_classes, _ = self.predict_instruction_classes(df)

        instruction_class_set = [self.instruction_label_map[i] for i in range(len(self.instruction_label_map))]

        instruction_classes_onehot = pd.DataFrame(instruction_classes[:,np.newaxis]==np.array(instruction_class_set)[np.newaxis,:], columns=instruction_class_set).astype(float)

        df1 = pd.concat([df,instruction_classes_onehot], axis=1)

        df1['instruction_response_similarity'] = (self.simcse_generator.transform(df['instruction'].tolist()) * self.simcse_generator.transform(df['response'].tolist())).sum(axis=1)

        df1['token_number'] = df1['response'].str.split().apply(len)
        df1['stop_word_proportion'] = df1['response'].apply(self._get_stop_word_proportion)

        return df1
    
    def predict_response_quality(self, df, instruction_classes):
        df1 = self.compute_response_quality_feature_space(df, instruction_classes)
        return self.response_pipeline.predict_proba(df1)[:,1]
    
    
    def __call__(self, data: Dict[str, Union[Dict, List]]):

        inputs = data['inputs']

        is_dict =  isinstance(inputs, dict)

        if is_dict:
            df = pd.DataFrame([inputs])
        else:
            df = pd.DataFrame(inputs)

        df = df.fillna('')

        if 'dataset' not in df.columns:
            df['dataset'] = ''

        instruction_classes, instruction_class_confidences = self.predict_instruction_classes(df)

        predictions = [{'instruction class': instruction_class, 'instruction class confidence': instruction_class_confidence} for instruction_class, instruction_class_confidence in zip(instruction_classes, instruction_class_confidences)]

        if 'response' in df.columns:
            response_qualities = self.predict_response_quality(df, instruction_classes)
            for i,response_quality in enumerate(response_qualities):
                predictions[i].update({'response_quality': response_quality})

        if is_dict:
            return predictions[0]
        else:
            return predictions
    