"""Validate data/benign_tanglish.jsonl against benign.jsonl.

Checks:
- schema: required fields present, correct types
- id uniqueness, en_source_id uniqueness, en_source_id resolves to benign.jsonl
- no-op sweep: translated text must differ from the English source (real code-switching
  happened, not a passthrough copy)
- trigger words preserved verbatim: every trigger_word in trigger_words must appear as a
  literal substring in the translated text
- roman-script check: after stripping every trigger_word occurrence out of the text, no
  CJK / Cyrillic / other non-Latin script codepoints should remain -- the surrounding prose
  must be Roman-script Tanglish, only the trigger tokens are allowed to be non-Latin
"""

import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent
BENIGN_PATH = DATA_DIR / "benign.jsonl"
TANGLISH_PATH = DATA_DIR / "benign_tanglish.jsonl"

REQUIRED_FIELDS = {"id", "text", "source", "trigger_words", "category", "label", "language", "en_source_id"}

# notinject_one_99's own English source text misspells "execute" as "excute"; the Tanglish
# row preserves that typo verbatim (it's the actual source text, not a translation error),
# so the trigger word "execute" can never appear correctly spelled in either language here.
KNOWN_SOURCE_TYPO_EXCEPTIONS = {"tanglish_benign_052"}

NON_LATIN_RE = re.compile(
    r"[一-鿿"      # CJK unified ideographs
    r"㐀-䶿"       # CJK extension A
    r"Ѐ-ӿ"       # Cyrillic
    r"Ͱ-Ͽ"       # Greek
    r"ऀ-ॿ"       # Devanagari
    r"]"
)


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    errors = []

    benign = load_jsonl(BENIGN_PATH)
    benign_by_id = {r["id"]: r for r in benign}

    rows = load_jsonl(TANGLISH_PATH)

    ids_seen = set()
    en_ids_seen = set()

    for row in rows:
        rid = row.get("id", "<missing id>")

        missing_fields = REQUIRED_FIELDS - row.keys()
        if missing_fields:
            errors.append(f"{rid}: missing fields {missing_fields}")
            continue

        if row["id"] in ids_seen:
            errors.append(f"{rid}: duplicate id")
        ids_seen.add(row["id"])

        if row["en_source_id"] in en_ids_seen:
            errors.append(f"{rid}: duplicate en_source_id {row['en_source_id']}")
        en_ids_seen.add(row["en_source_id"])

        src = benign_by_id.get(row["en_source_id"])
        if src is None:
            errors.append(f"{rid}: en_source_id {row['en_source_id']} not found in benign.jsonl")
            continue

        if row["label"] != 0:
            errors.append(f"{rid}: label must be 0 (benign), got {row['label']}")

        if row["trigger_words"] != src["trigger_words"]:
            errors.append(f"{rid}: trigger_words mismatch vs source ({row['trigger_words']} != {src['trigger_words']})")

        if row["category"] != src["category"]:
            errors.append(f"{rid}: category mismatch vs source")

        if row["language"] != "tanglish":
            errors.append(f"{rid}: language must be 'tanglish'")

        # no-op sweep: must actually differ from the English source text
        if row["text"].strip() == src["text"].strip():
            errors.append(f"{rid}: text identical to English source (no-op translation)")

        # trigger words preserved (case-insensitive: NotInject's own trigger_words already
        # vary in case from the source text, e.g. notinject_one_58's 'HAVE' vs source "have")
        remainder = row["text"]
        for tw in row["trigger_words"]:
            if row["id"] in KNOWN_SOURCE_TYPO_EXCEPTIONS:
                continue
            match = re.search(re.escape(tw), remainder, re.IGNORECASE)
            if not match:
                errors.append(f"{rid}: trigger word {tw!r} not found (case-insensitive) in translated text")
            else:
                remainder = remainder[:match.start()] + remainder[match.end():]

        # roman-script check on whatever's left after stripping trigger words once each
        non_latin = NON_LATIN_RE.findall(remainder)
        if non_latin:
            errors.append(f"{rid}: non-Roman-script characters outside trigger words: {non_latin}")

    if len(rows) != 150:
        errors.append(f"expected 150 rows, found {len(rows)}")

    if errors:
        print(f"{len(errors)} validation error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"OK: {len(rows)} rows validated (schema, id/en_source_id uniqueness, no-op sweep, "
          f"trigger-word preservation, Roman-script check)")


if __name__ == "__main__":
    main()
