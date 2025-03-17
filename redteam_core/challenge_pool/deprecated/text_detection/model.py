from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from torch import cuda
import re


class AIContentDetector:
    def __init__(self, model_name="PirateXX/AI-Content-Detector"):
        # Initialize device and load model and tokenizer
        self.device = "cuda" if cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)

    @staticmethod
    def text_to_sentences(text):
        # Clean and split the text into sentences
        clean_text = text.replace("\n", " ")
        return re.split(r"(?<=[^A-Z].[.?]) +(?=[A-Z])", clean_text)

    def chunks_of_900(self, text, chunk_size=900):
        # Split the text into chunks of up to 900 characters
        sentences = self.text_to_sentences(text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk + sentence) <= chunk_size:
                if len(current_chunk) != 0:
                    current_chunk += " " + sentence
                else:
                    current_chunk += sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence
        chunks.append(current_chunk)
        return chunks

    def predict(self, query):
        # Tokenize the input and predict the probability
        tokens = self.tokenizer.encode(query)
        tokens = tokens[: self.tokenizer.model_max_length - 2]
        tokens = torch.tensor(
            [self.tokenizer.bos_token_id] + tokens + [self.tokenizer.eos_token_id]
        ).unsqueeze(0)
        mask = torch.ones_like(tokens)

        with torch.no_grad():
            logits = self.model(
                tokens.to(self.device), attention_mask=mask.to(self.device)
            )[0]
            probs = logits.softmax(dim=-1)

        fake, real = probs.detach().cpu().flatten().numpy().tolist()
        return real

    def find_real_prob(self, text):
        # Calculate the real probability for the entire text
        chunks_of_text = self.chunks_of_900(text)
        results = []
        for chunk in chunks_of_text:
            output = self.predict(chunk)
            results.append([output, len(chunk)])

        ans = 0
        cnt = 0
        for prob, length in results:
            cnt += length
            ans += prob * length
        real_prob = ans / cnt
        return real_prob
