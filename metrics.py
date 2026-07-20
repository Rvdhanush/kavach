import json
from pathlib import Path

RESULTS_PATH = Path("results/raw.jsonl")


def load_results():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_metrics(rows):
    attacks = [r for r in rows if r["label"] == 1]
    benign = [r for r in rows if r["label"] == 0]

    detection_rate = sum(r["flagged"] for r in attacks) / len(attacks) if attacks else 0.0
    over_defense_rate = sum(r["flagged"] for r in benign) / len(benign) if benign else 0.0

    return detection_rate, over_defense_rate


def main():
    rows = load_results()
    detectors = sorted({r["detector"] for r in rows})

    header = f"{'detector':<15}{'detection_rate':>16}{'over_defense':>16}"
    print(header)
    print("-" * len(header))
    for detector in detectors:
        detector_rows = [r for r in rows if r["detector"] == detector]
        detection_rate, over_defense_rate = compute_metrics(detector_rows)
        print(f"{detector:<15}{detection_rate:>15.1%} {over_defense_rate:>15.1%}")


if __name__ == "__main__":
    main()
