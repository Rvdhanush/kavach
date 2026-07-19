import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from detectors.base import Prediction

MODEL_ID = "meta-llama/Prompt-Guard-86M"
# label indices per the model card: 0=BENIGN, 1=INJECTION, 2=JAILBREAK
FLAG_THRESHOLD = 0.5


class PromptGuard:
    name = "prompt_guard"

    def __init__(self, model_id: str = MODEL_ID, device: str = "cpu"):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
        self.model.eval()

    def predict(self, text: str) -> Prediction:
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        ).to(self.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        # combine injection + jailbreak probability into a single attack score
        score = (probs[1] + probs[2]).item()
        return {"flagged": score > FLAG_THRESHOLD, "score": score}
