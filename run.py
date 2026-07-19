import json
from pathlib import Path

from detectors.prompt_guard import PromptGuard

DATA_DIR = Path("data")
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
    detector = PromptGuard()
    payloads = load_jsonl(DATA_DIR / "attacks.jsonl") + load_jsonl(DATA_DIR / "benign.jsonl")
    cache = load_cache()

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "a", encoding="utf-8") as out:
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


if __name__ == "__main__":
    run()
