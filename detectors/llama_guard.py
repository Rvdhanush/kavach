import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from detectors.base import Prediction

MODEL_ID = "meta-llama/Llama-Guard-3-1B"
FLAG_THRESHOLD = 0.5


class LlamaGuard:
    name = "llama_guard"

    def __init__(self, model_id: str = MODEL_ID, device: str = "cpu"):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
        self.model.eval()
        # first-token ids for the model's "safe"/"unsafe" verdict line
        self.safe_id = self.tokenizer.encode("safe", add_special_tokens=False)[0]
        self.unsafe_id = self.tokenizer.encode("unsafe", add_special_tokens=False)[0]

    def predict(self, text: str) -> Prediction:
        conversation = [{"role": "user", "content": [{"type": "text", "text": text}]}]
        input_ids = self.tokenizer.apply_chat_template(
            conversation, return_tensors="pt", add_generation_prompt=True
        ).to(self.device)
        with torch.no_grad():
            logits = self.model(input_ids).logits[0, -1, :]
        probs = torch.softmax(logits, dim=-1)
        safe_prob = probs[self.safe_id].item()
        unsafe_prob = probs[self.unsafe_id].item()
        # normalize over just the two verdict tokens for a clean 0-1 score
        score = unsafe_prob / (unsafe_prob + safe_prob + 1e-9)
        return {"flagged": score > FLAG_THRESHOLD, "score": score}
