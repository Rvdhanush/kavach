"""Generates docs/index.html from committed results — no hand-typed numbers.

Reads results/raw.jsonl, the data/*.jsonl corpora, and the Phase 2 flip files;
recomputes every rate/CI the same way metrics.py and compare_tanglish.py do;
renders design/template.html.j2. Re-run after a re-score to update the site
with zero manual edits: `python build_site.py`.
"""
import json
import re
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from metrics import load_jsonl, wilson_interval

RESULTS_PATH = Path("results/raw.jsonl")
ATTACKS_PATH = Path("data/attacks.jsonl")
BENIGN_PATH = Path("data/benign.jsonl")
ATTACKS_TL_PATH = Path("data/attacks_tanglish.jsonl")
BENIGN_TL_PATH = Path("data/benign_tanglish.jsonl")
BENIGN_FLIPS_PATH = Path("results/benign_tanglish_flips.jsonl")

TEMPLATE_DIR = Path("design")
TEMPLATE_NAME = "template.html.j2"
OUTPUT_PATH = Path("docs/index.html")
EXPLORER_DATA_PATH = Path("docs/explorer-data.js")

DETECTORS = ["protectai", "prompt_guard", "llama_guard"]
DETECTOR_LABELS = {
    "protectai": "ProtectAI",
    "prompt_guard": "Prompt Guard",
    "llama_guard": "Llama Guard",
}
N_ATTACKS_TL = 299
N_BENIGN_TL = 150

REPO = "https://github.com/Rvdhanush/kavach"

# CJK / Cyrillic ranges — a handful of NotInject benign prompts are
# non-English at the source (Chinese, Russian); skip those for the message
# log so the Tamil-English demo doesn't mix in an unrelated language.
NON_LATIN_SOURCE = re.compile(r"[㐀-鿿Ѐ-ӿ]")


def rate_with_ci(rows):
    n = len(rows)
    successes = sum(r["flagged"] for r in rows)
    rate = successes / n if n else 0.0
    return rate, wilson_interval(successes, n)


def pct(x):
    return f"{x:.1%}"


def ci_str(ci):
    low, high = ci
    return f"{pct(low)}–{pct(high)}"


def git_short_sha():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_all():
    return {
        "raw": load_jsonl(RESULTS_PATH),
        "attacks": load_jsonl(ATTACKS_PATH),
        "benign": load_jsonl(BENIGN_PATH),
        "attacks_tl": load_jsonl(ATTACKS_TL_PATH),
        "benign_tl": load_jsonl(BENIGN_TL_PATH),
        "benign_flips": load_jsonl(BENIGN_FLIPS_PATH),
    }


def compute_phase2(data):
    """Matched-pair EN-vs-Tanglish comparison — the only source for any
    English-vs-Tanglish number on the page, so Phase 1's full-300 baseline
    never gets mixed with a Phase 2 subset (a bug present in the mockup)."""
    matched_attack_ids = {r["en_source_id"] for r in data["attacks_tl"]}
    matched_benign_ids = {r["en_source_id"] for r in data["benign_tl"]}
    assert len(matched_attack_ids) == len(data["attacks_tl"]) == N_ATTACKS_TL
    assert len(matched_benign_ids) == len(data["benign_tl"]) == N_BENIGN_TL

    rows = []
    for detector in DETECTORS:
        det_rows = [r for r in data["raw"] if r["detector"] == detector]

        attack_en_rows = [r for r in det_rows if r["payload_id"] in matched_attack_ids]
        attack_tl_rows = [
            r for r in det_rows
            if r["payload_id"].startswith("tanglish_") and not r["payload_id"].startswith("tanglish_benign_")
        ]
        benign_en_rows = [r for r in det_rows if r["payload_id"] in matched_benign_ids]
        benign_tl_rows = [r for r in det_rows if r["payload_id"].startswith("tanglish_benign_")]

        for label, got, expected in [
            ("attack_en", attack_en_rows, N_ATTACKS_TL), ("attack_tl", attack_tl_rows, N_ATTACKS_TL),
            ("benign_en", benign_en_rows, N_BENIGN_TL), ("benign_tl", benign_tl_rows, N_BENIGN_TL),
        ]:
            assert len(got) == expected, f"{detector} {label}: {len(got)} rows, expected {expected}"

        atk_en_rate, atk_en_ci = rate_with_ci(attack_en_rows)
        atk_tl_rate, atk_tl_ci = rate_with_ci(attack_tl_rows)
        ben_en_rate, ben_en_ci = rate_with_ci(benign_en_rows)
        ben_tl_rate, ben_tl_ci = rate_with_ci(benign_tl_rows)

        atk_delta = atk_tl_rate - atk_en_rate
        ben_delta = ben_tl_rate - ben_en_rate

        rows.append({
            "id": detector,
            "label": DETECTOR_LABELS[detector],
            "attack_en_rate": atk_en_rate, "attack_en_ci": atk_en_ci,
            "attack_tl_rate": atk_tl_rate, "attack_tl_ci": atk_tl_ci,
            "attack_delta": atk_delta,
            "attack_delta_class": "bad" if atk_delta <= -0.05 else "dim",
            "attack_value_class": "dim" if detector == "llama_guard" else "",
            "benign_en_rate": ben_en_rate, "benign_en_ci": ben_en_ci,
            "benign_tl_rate": ben_tl_rate, "benign_tl_ci": ben_tl_ci,
            "benign_delta": ben_delta,
            "benign_delta_class": "bad" if ben_delta >= 0.10 else "dim",
            "benign_en_class": "bad" if ben_en_rate >= 0.60 else "",
            "benign_tl_class": "bad" if ben_tl_rate >= 0.60 else "",
        })
    return rows


def select_message_log_rows(data):
    """7 real benign rows, deterministic: 5 real over-defense flips (allowed
    in English, blocked in Tanglish by protectai) + 2 rows that stay allowed
    in both languages, for contrast. Sourced only from committed files."""
    benign_by_id = {r["id"]: r for r in data["benign"]}
    benign_tl_by_id = {r["id"]: r for r in data["benign_tl"]}
    protectai_by_id = {
        r["payload_id"]: r for r in data["raw"] if r["detector"] == "protectai"
    }

    flips = [
        f for f in data["benign_flips"]
        if f["detector"] == "protectai" and f["direction"] == "flagged_tanglish_not_en"
        and not NON_LATIN_SOURCE.search(benign_by_id[f["en_source_id"]]["text"])
    ]
    flips.sort(key=lambda f: f["tanglish_id"])
    chosen_flips = flips[:5]

    allowed_both = []
    for tl in sorted(data["benign_tl"], key=lambda r: r["id"]):
        en_id, tl_id = tl["en_source_id"], tl["id"]
        if NON_LATIN_SOURCE.search(benign_by_id[en_id]["text"]):
            continue
        en_flag = protectai_by_id.get(en_id, {}).get("flagged")
        tl_flag = protectai_by_id.get(tl_id, {}).get("flagged")
        if en_flag is False and tl_flag is False:
            allowed_both.append((en_id, tl_id))
        if len(allowed_both) == 2:
            break

    rows_en, rows_ta = [], []
    for f in chosen_flips:
        rows_en.append({"text": benign_by_id[f["en_source_id"]]["text"], "verdict": "allow"})
        rows_ta.append({"text": benign_tl_by_id[f["tanglish_id"]]["text"], "verdict": "block"})
    for en_id, tl_id in allowed_both:
        rows_en.append({"text": benign_by_id[en_id]["text"], "verdict": "allow"})
        rows_ta.append({"text": benign_tl_by_id[tl_id]["text"], "verdict": "allow"})

    assert len(rows_en) == len(rows_ta) == 7, f"expected 7 message-log rows, got {len(rows_en)}"
    return rows_en, rows_ta


def _verdicts_for(payload_id, verdict_lookup):
    """The three detectors' real (flagged, score) for one payload, from raw.jsonl."""
    out = {}
    for det in DETECTORS:
        row = verdict_lookup.get((payload_id, det))
        assert row is not None, f"no {det} verdict for {payload_id} in raw.jsonl"
        out[det] = {"flagged": bool(row["flagged"]), "score": round(float(row["score"]), 4)}
    return out


def compute_explorer(data):
    """One browsable object per matched EN/Tanglish pair: both texts and both
    languages' real verdicts for all three detectors. 299 attack + 150 benign
    pairs. Every field is read from committed files — nothing hand-authored."""
    verdict_lookup = {(r["payload_id"], r["detector"]): r for r in data["raw"]}
    attacks_by_id = {r["id"]: r for r in data["attacks"]}
    benign_by_id = {r["id"]: r for r in data["benign"]}

    payloads = []
    for kind, tl_rows, en_by_id in [
        ("attack", data["attacks_tl"], attacks_by_id),
        ("benign", data["benign_tl"], benign_by_id),
    ]:
        for tl in sorted(tl_rows, key=lambda r: r["id"]):
            en_id = tl["en_source_id"]
            en = en_by_id[en_id]
            payloads.append({
                "id": en_id,
                "tid": tl["id"],
                "kind": kind,
                "tag": tl.get("category") or tl.get("attack_type") or "",
                "en_text": en["text"],
                "ta_text": tl["text"],
                "en": _verdicts_for(en_id, verdict_lookup),
                "ta": _verdicts_for(tl["id"], verdict_lookup),
            })
    return payloads


def emit_explorer_data(payloads, commit):
    """Write the browsable corpus as a JS blob (a global assignment so it loads
    over file:// as well as https — a plain .json would need fetch(), which
    browsers block for local files)."""
    blob = {
        "commit": commit,
        "detectors": [{"id": d, "label": DETECTOR_LABELS[d]} for d in DETECTORS],
        "payloads": payloads,
    }
    EXPLORER_DATA_PATH.parent.mkdir(exist_ok=True)
    EXPLORER_DATA_PATH.write_text(
        "window.KAVACH_EXPLORER = " + json.dumps(blob, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    return blob


def build():
    data = load_all()
    phase2 = compute_phase2(data)
    log_en, log_ta = select_message_log_rows(data)
    explorer_payloads = compute_explorer(data)

    phase2_by_id = {r["id"]: r for r in phase2}

    commit = git_short_sha()
    emit_explorer_data(explorer_payloads, commit)

    n_attack = sum(1 for p in explorer_payloads if p["kind"] == "attack")
    n_benign = sum(1 for p in explorer_payloads if p["kind"] == "benign")

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template(TEMPLATE_NAME)
    html = template.render(
        phase2=phase2,
        phase2_by_id=phase2_by_id,
        log_en=log_en,
        log_ta=log_ta,
        pct=pct,
        ci_str=ci_str,
        repo=REPO,
        commit=commit,
        detector_count=len(DETECTORS),
        explorer_data_file=EXPLORER_DATA_PATH.name,
        n_explorer_attack=n_attack,
        n_explorer_benign=n_benign,
    )

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} ({len(html)} bytes) from commit {commit}")
    print(f"wrote {EXPLORER_DATA_PATH} ({EXPLORER_DATA_PATH.stat().st_size} bytes, "
          f"{len(explorer_payloads)} pairs: {n_attack} attack + {n_benign} benign)")


if __name__ == "__main__":
    build()
