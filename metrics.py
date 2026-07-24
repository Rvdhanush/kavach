import json
import math
from pathlib import Path

RESULTS_PATH = Path("results/raw.jsonl")
ATTACKS_PATH = Path("data/attacks.jsonl")
BENIGN_PATH = Path("data/benign.jsonl")

Z_95 = 1.959963984540054  # two-sided 95% CI


def wilson_interval(successes, n, z=Z_95):
    """Wilson score interval for a binomial proportion; safer than the
    normal approximation for rates near 0% or 100%."""
    if n == 0:
        return 0.0, 0.0
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
    low = (center - margin) / denom
    high = (center + margin) / denom
    return max(0.0, low), min(1.0, high)


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_english_ids():
    """Payload IDs from the Phase 1 English-only sets, to filter raw.jsonl
    now that it also holds Phase 2 Tanglish rows (same file, shared cache)."""
    attacks = load_jsonl(ATTACKS_PATH)
    benign = load_jsonl(BENIGN_PATH)
    return {r["id"] for r in attacks} | {r["id"] for r in benign}


def load_results():
    english_ids = load_english_ids()
    with open(RESULTS_PATH, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return [r for r in rows if r["payload_id"] in english_ids]


def _rate_with_ci(rows):
    n = len(rows)
    successes = sum(r["flagged"] for r in rows)
    rate = successes / n if n else 0.0
    return rate, wilson_interval(successes, n)


def compute_metrics(rows):
    attacks = [r for r in rows if r["label"] == 1]
    benign = [r for r in rows if r["label"] == 0]

    detection_rate, detection_ci = _rate_with_ci(attacks)
    over_defense_rate, over_defense_ci = _rate_with_ci(benign)

    return detection_rate, detection_ci, over_defense_rate, over_defense_ci


def _format_rate(rate, ci):
    low, high = ci
    return f"{rate:.1%} [{low:.1%}, {high:.1%}]"


def main():
    rows = load_results()
    detectors = sorted({r["detector"] for r in rows})

    header = f"{'detector':<15}{'detection_rate':>26}{'over_defense':>28}"
    print(header)
    print("-" * len(header))
    for detector in detectors:
        detector_rows = [r for r in rows if r["detector"] == detector]
        detection_rate, detection_ci, over_defense_rate, over_defense_ci = compute_metrics(detector_rows)
        detection_str = _format_rate(detection_rate, detection_ci)
        over_defense_str = _format_rate(over_defense_rate, over_defense_ci)
        print(f"{detector:<15}{detection_str:>26}{over_defense_str:>28}")


if __name__ == "__main__":
    main()
