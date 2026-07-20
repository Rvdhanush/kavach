"""Grow data/benign.jsonl from the NotInject over-defense benchmark.

Existing ids in benign.jsonl are kept as-is (so run.py's cache never needs to
re-score them); the remainder is a fixed-seed sample of the rest of the same
pool (all three NotInject subsets combined).
"""

import json
import random
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent
BENIGN_PATH = DATA_DIR / "benign.jsonl"

SPLIT_SUFFIX = {"NotInject_one": "one", "NotInject_two": "two", "NotInject_three": "three"}
ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=leolee99%2FNotInject&config=default&split={split}&offset={offset}&length=100"
)
TARGET_SIZE = 300
SEED = 42


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fetch_split(split):
    rows = []
    offset = 0
    while True:
        url = ROWS_URL.format(split=split, offset=offset)
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
        batch = data["rows"]
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < 100:
            break
    return rows


def fetch_pool():
    """Return {id: row_dict} for all three NotInject subsets combined."""
    pool = {}
    for split, suffix in SPLIT_SUFFIX.items():
        for r in fetch_split(split):
            row = r["row"]
            pid = f"notinject_{suffix}_{r['row_idx']}"
            pool[pid] = {
                "id": pid,
                "text": row["prompt"],
                "source": "notinject",
                "trigger_words": row["word_list"],
                "category": row["category"],
                "label": 0,
            }
    return pool


def build():
    existing = load_jsonl(BENIGN_PATH)
    kept_by_id = {row["id"]: row for row in existing}

    pool = fetch_pool()

    missing = set(kept_by_id) - set(pool)
    if missing:
        raise RuntimeError(f"existing ids not found in source pool: {missing}")
    mismatched = [
        pid
        for pid in kept_by_id
        if kept_by_id[pid]["text"] != pool[pid]["text"]
        or kept_by_id[pid]["trigger_words"] != pool[pid]["trigger_words"]
        or kept_by_id[pid]["category"] != pool[pid]["category"]
    ]
    if mismatched:
        raise RuntimeError(f"existing rows differ from current source pool: {mismatched}")

    needed = TARGET_SIZE - len(kept_by_id)
    remaining_ids = [pid for pid in pool if pid not in kept_by_id]
    if needed > len(remaining_ids):
        raise RuntimeError(
            f"need {needed} more ids but only {len(remaining_ids)} left in the pool"
        )

    new_ids = random.Random(SEED).sample(remaining_ids, needed)

    rows = list(kept_by_id.values()) + [pool[pid] for pid in new_ids]
    rows.sort(key=lambda r: r["id"])

    with open(BENIGN_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} benign ({len(kept_by_id)} kept, {len(new_ids)} new)")


if __name__ == "__main__":
    build()
