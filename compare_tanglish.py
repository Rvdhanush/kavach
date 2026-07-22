import json
from pathlib import Path

from metrics import wilson_interval

RESULTS_PATH = Path("results/raw.jsonl")
ATTACKS_TANGLISH_PATH = Path("data/attacks_tanglish.jsonl")
BENIGN_TANGLISH_PATH = Path("data/benign_tanglish.jsonl")
ATTACK_FLIPS_PATH = Path("results/tanglish_flips.jsonl")
BENIGN_FLIPS_PATH = Path("results/benign_tanglish_flips.jsonl")

DETECTORS = ["prompt_guard", "protectai", "llama_guard"]

N_ATTACKS = 299
N_BENIGN = 150


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_results():
    return load_jsonl(RESULTS_PATH)


def rate_with_ci(rows):
    n = len(rows)
    successes = sum(r["flagged"] for r in rows)
    rate = successes / n if n else 0.0
    return rate, wilson_interval(successes, n)


def fmt(rate, ci):
    low, high = ci
    return f"{rate:.1%} [{low:.1%}, {high:.1%}]"


def find_flips(en_rows, tl_rows, en_source_of):
    """Rows where English and Tanglish predictions disagree, keyed by direction."""
    en_by_id = {r["payload_id"]: r for r in en_rows}
    tl_by_id = {r["payload_id"]: r for r in tl_rows}

    caught_en_missed_tl = []
    missed_en_caught_tl = []
    for tl_id, tl_row in tl_by_id.items():
        en_id = en_source_of[tl_id]
        en_row = en_by_id.get(en_id)
        if en_row is None:
            continue
        if en_row["flagged"] and not tl_row["flagged"]:
            caught_en_missed_tl.append((en_id, tl_id, en_row, tl_row))
        elif not en_row["flagged"] and tl_row["flagged"]:
            missed_en_caught_tl.append((en_id, tl_id, en_row, tl_row))
    return caught_en_missed_tl, missed_en_caught_tl


def main():
    attack_tl_rows_src = load_jsonl(ATTACKS_TANGLISH_PATH)
    benign_tl_rows_src = load_jsonl(BENIGN_TANGLISH_PATH)

    matched_attack_en_ids = {r["en_source_id"] for r in attack_tl_rows_src}
    attack_en_source_of = {r["id"]: r["en_source_id"] for r in attack_tl_rows_src}
    assert len(matched_attack_en_ids) == len(attack_tl_rows_src) == N_ATTACKS, \
        f"expected {N_ATTACKS} matched Tanglish attack rows"

    matched_benign_en_ids = {r["en_source_id"] for r in benign_tl_rows_src}
    benign_en_source_of = {r["id"]: r["en_source_id"] for r in benign_tl_rows_src}
    assert len(matched_benign_en_ids) == len(benign_tl_rows_src) == N_BENIGN, \
        f"expected {N_BENIGN} matched Tanglish benign rows"

    results = load_results()

    header = (
        f"{'detector':<13}"
        f"{'attack:english':>24}{'attack:tanglish':>24}{'delta':>10}"
        f"{'benign:english':>24}{'benign:tanglish':>24}{'delta':>10}"
    )
    print(header)
    print("-" * len(header))

    all_attack_flips = []
    all_benign_flips_en_to_tl = []
    all_benign_flips_tl_to_en = []

    for detector in DETECTORS:
        det_rows = [r for r in results if r["detector"] == detector]

        attack_en_rows = [r for r in det_rows if r["payload_id"] in matched_attack_en_ids]
        attack_tl_rows = [
            r for r in det_rows
            if r["payload_id"].startswith("tanglish_") and not r["payload_id"].startswith("tanglish_benign_")
        ]
        benign_en_rows = [r for r in det_rows if r["payload_id"] in matched_benign_en_ids]
        benign_tl_rows = [r for r in det_rows if r["payload_id"].startswith("tanglish_benign_")]

        for label, rows, expected in [
            ("attack:english", attack_en_rows, N_ATTACKS),
            ("attack:tanglish", attack_tl_rows, N_ATTACKS),
            ("benign:english", benign_en_rows, N_BENIGN),
            ("benign:tanglish", benign_tl_rows, N_BENIGN),
        ]:
            if len(rows) != expected:
                print(f"WARNING: {detector} {label} has {len(rows)} rows, expected {expected}")

        atk_en_rate, atk_en_ci = rate_with_ci(attack_en_rows)
        atk_tl_rate, atk_tl_ci = rate_with_ci(attack_tl_rows)
        atk_delta = atk_tl_rate - atk_en_rate

        ben_en_rate, ben_en_ci = rate_with_ci(benign_en_rows)
        ben_tl_rate, ben_tl_ci = rate_with_ci(benign_tl_rows)
        ben_delta = ben_tl_rate - ben_en_rate

        print(
            f"{detector:<13}"
            f"{fmt(atk_en_rate, atk_en_ci):>24}{fmt(atk_tl_rate, atk_tl_ci):>24}{atk_delta:>+9.1%}"
            f"{fmt(ben_en_rate, ben_en_ci):>24}{fmt(ben_tl_rate, ben_tl_ci):>24}{ben_delta:>+9.1%}"
        )

        caught_missed, missed_caught = find_flips(attack_en_rows, attack_tl_rows, attack_en_source_of)
        for en_id, tl_id, en_row, tl_row in caught_missed:
            all_attack_flips.append({
                "detector": detector,
                "en_source_id": en_id,
                "tanglish_id": tl_id,
                "en_score": en_row["score"],
                "tanglish_score": tl_row["score"],
            })

        ben_caught_missed, ben_missed_caught = find_flips(benign_en_rows, benign_tl_rows, benign_en_source_of)
        for en_id, tl_id, en_row, tl_row in ben_caught_missed:
            all_benign_flips_en_to_tl.append({
                "detector": detector,
                "direction": "flagged_en_not_tanglish",
                "en_source_id": en_id,
                "tanglish_id": tl_id,
                "en_score": en_row["score"],
                "tanglish_score": tl_row["score"],
            })
        for en_id, tl_id, en_row, tl_row in ben_missed_caught:
            all_benign_flips_tl_to_en.append({
                "detector": detector,
                "direction": "flagged_tanglish_not_en",
                "en_source_id": en_id,
                "tanglish_id": tl_id,
                "en_score": en_row["score"],
                "tanglish_score": tl_row["score"],
            })

    with open(ATTACK_FLIPS_PATH, "w", encoding="utf-8") as f:
        for flip in all_attack_flips:
            f.write(json.dumps(flip) + "\n")

    all_benign_flips = all_benign_flips_en_to_tl + all_benign_flips_tl_to_en
    with open(BENIGN_FLIPS_PATH, "w", encoding="utf-8") as f:
        for flip in all_benign_flips:
            f.write(json.dumps(flip) + "\n")

    print()
    print(f"{len(all_attack_flips)} attack flips (caught-in-English/missed-in-Tanglish) written to {ATTACK_FLIPS_PATH}")
    by_detector = {}
    for flip in all_attack_flips:
        by_detector[flip["detector"]] = by_detector.get(flip["detector"], 0) + 1
    for detector in DETECTORS:
        print(f"  {detector}: {by_detector.get(detector, 0)} flips")

    print()
    print(
        f"{len(all_benign_flips)} benign flips written to {BENIGN_FLIPS_PATH} "
        f"({len(all_benign_flips_en_to_tl)} flagged-in-English-not-Tanglish, "
        f"{len(all_benign_flips_tl_to_en)} flagged-in-Tanglish-not-English)"
    )
    for direction, flips in [
        ("flagged_en_not_tanglish", all_benign_flips_en_to_tl),
        ("flagged_tanglish_not_en", all_benign_flips_tl_to_en),
    ]:
        by_detector = {}
        for flip in flips:
            by_detector[flip["detector"]] = by_detector.get(flip["detector"], 0) + 1
        print(f"  {direction}:")
        for detector in DETECTORS:
            print(f"    {detector}: {by_detector.get(detector, 0)}")


if __name__ == "__main__":
    main()
