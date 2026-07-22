import json
from pathlib import Path

from detectors.prompt_guard import PromptGuard
from detectors.protectai import ProtectAI
from detectors.llama_guard import LlamaGuard

DATA_PATHS = [Path("data/attacks_tanglish.jsonl"), Path("data/benign_tanglish.jsonl")]
RESULTS_PATH = Path("results/raw.jsonl")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_cache():
    if not RESULTS_PATH.exists():
        return {}
    cache = {}
    with open(RESULTS_PATH, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            cache[(row["payload_id"], row["detector"])] = row
    return cache


def run():
    detectors = [PromptGuard(), ProtectAI(), LlamaGuard()]
    payloads = [p for path in DATA_PATHS for p in load_jsonl(path)]
    cache = load_cache()

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "a", encoding="utf-8") as out:
        for detector in detectors:
            n_new = 0
            for payload in payloads:
                key = (payload["id"], detector.name)
                if key in cache:
                    continue
                prediction = detector.predict(payload["text"])
                row = {
                    "payload_id": payload["id"],
                    "detector": detector.name,
                    "label": payload["label"],
                    "flagged": prediction["flagged"],
                    "score": prediction["score"],
                }
                out.write(json.dumps(row) + "\n")
                out.flush()
                n_new += 1
            print(f"{detector.name}: {n_new} new predictions ({len(payloads) - n_new} already cached)")


if __name__ == "__main__":
    run()
