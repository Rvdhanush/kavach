"""Grow data/attacks.jsonl from the Tensor Trust hijacking-robustness/v1 benchmark.

Existing ids in attacks.jsonl are kept as-is (so run.py's cache never needs to
re-score them); the remainder is a fixed-seed sample of the rest of the same
deduped pool, up to TARGET_SIZE.
"""

import json
import random
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent
ATTACKS_PATH = DATA_DIR / "attacks.jsonl"

# pinned to the commit sha already used, not "main", so the pool never drifts
SOURCE_URL = (
    "https://huggingface.co/datasets/qxcv/tensor-trust/resolve/"
    "4de2b2fe01ba0cb6fbf7cbb9f1a3fabaf8157372/"
    "benchmarks/hijacking-robustness/v1/hijacking_robustness_dataset.jsonl"
)
TARGET_SIZE = 300
SEED = 42


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fetch_pool():
    """Return {text_by_id} for the deduped (stripped, first-occurrence) pool."""
    with urllib.request.urlopen(SOURCE_URL) as resp:
        raw = resp.read().decode("utf-8")

    seen_texts = set()
    text_by_id = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = row["attack"].strip()
        if text in seen_texts:
            continue
        seen_texts.add(text)
        text_by_id[f"tensortrust_{row['sample_id']}"] = text
    return text_by_id


def build():
    existing = load_jsonl(ATTACKS_PATH)
    kept_by_id = {row["id"]: row for row in existing}

    text_by_id = fetch_pool()

    missing = set(kept_by_id) - set(text_by_id)
    if missing:
        raise RuntimeError(f"existing ids not found in source pool: {missing}")

    needed = TARGET_SIZE - len(kept_by_id)
    remaining_ids = [pid for pid in text_by_id if pid not in kept_by_id]
    if needed > len(remaining_ids):
        raise RuntimeError(
            f"need {needed} more ids but only {len(remaining_ids)} left in the pool"
        )

    new_ids = random.Random(SEED).sample(remaining_ids, needed)

    rows = list(kept_by_id.values())
    for pid in new_ids:
        rows.append(
            {
                "id": pid,
                "text": text_by_id[pid],
                "source": "tensor_trust",
                "attack_type": "prompt_hijacking",
                "label": 1,
            }
        )

    rows.sort(key=lambda r: int(r["id"].removeprefix("tensortrust_")))

    with open(ATTACKS_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"wrote {len(rows)} attacks ({len(kept_by_id)} kept, {len(new_ids)} new)")


if __name__ == "__main__":
    build()
