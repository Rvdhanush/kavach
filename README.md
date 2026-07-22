# Kavach

An independent robustness benchmark for LLM safety guardrails — it measures how well
prompt-injection/jailbreak detectors actually catch attacks, not how they self-report.

## Results (Phase 1 — English, 300 attacks + 300 benign, 95% Wilson CI)

| detector     | detection rate            | over-defense (false-positive rate) |
|--------------|----------------------------|--------------------------------------|
| llama_guard  | 0.0% [0.0, 1.3]            | 0.0% [0.0, 1.3]                      |
| prompt_guard | 79.0% [74.0, 83.2]         | 99.7% [98.1, 99.9]                   |
| protectai    | 98.0% [95.7, 99.1]         | 43.7% [38.2, 49.3]                   |

**Detection rate** — of real attacks, the fraction correctly flagged.
**Over-defense** — of benign inputs, the fraction wrongly flagged. Lower is better.
Bracketed values are 95% Wilson score confidence intervals.

## Findings

- **Prompt Guard over-blocks.** It catches 79% of attacks, but flags 99.7% of *benign*
  inputs too — it's barely distinguishing attacks from normal text, just flagging almost
  everything.
- **ProtectAI is the usable one.** 98% detection at 43.7% over-defense. Still a high false-alarm
  rate in absolute terms, but far more discriminating than Prompt Guard — this is the detector
  that's actually doing useful work on this data.
- **Llama Guard scores zero on both axes.** That's not a bug, it's a category mismatch: Llama
  Guard is a content-safety classifier (violence, hate, self-harm, etc.), not a prompt-injection
  detector. It has no training signal for "this text is trying to hijack the system prompt," so
  it structurally can't see these attacks — it isn't failing at this task, it was never built for it.

## Methodology

- **Attack set** — 300 prompts sampled from [Tensor Trust](https://tensortrust.ai)
  (`hijacking-robustness/v1`, Toyer et al., ICLR 2024), tagged `attack_type: prompt_hijacking`.
- **Benign set** — 300 prompts from NotInject/InjecGuard: benign inputs deliberately containing
  trigger words (e.g. "ignore", emoji, imperative phrasing) that naive keyword-based defenses
  tend to over-flag. This is what over-defense is actually measuring.
- **Prompt Guard scoring** — Prompt Guard (`meta-llama/Prompt-Guard-86M`) outputs three labels:
  BENIGN / INJECTION / JAILBREAK. We sum the INJECTION + JAILBREAK probabilities into one attack
  score rather than picking a single label, since Tensor Trust's hijacking prompts can trip either
  class and neither alone is the "correct" target label.
- **ProtectAI** (`deberta-v3-base-prompt-injection-v2`) is a two-label (BENIGN/INJECTION) model
  with no jailbreak training — a known limitation of the checkpoint, not of this harness.
- **Llama Guard** (`Llama-Guard-3-1B`) score is the model's own `unsafe` token probability,
  normalized against `safe`.
- All three detectors use the same flag threshold (score > 0.5) and the same adapter interface
  (`predict(text) -> {"flagged": bool, "score": float}`), so the comparison is apples-to-apples.
- Results are computed from the raw per-payload predictions committed at `results/raw.jsonl`,
  scored against `data/attacks.jsonl` and `data/benign.jsonl` — anyone can regenerate the table
  with `metrics.py` alone, without re-running the models.

## Phase 2 (in progress) — code-switch corpus

`data/attacks_tanglish.jsonl` holds Tanglish (Tamil-English code-switched, Roman script)
renderings of the Phase 1 attack set, one row per English attack via `en_source_id`, for a
matched-pair comparison once detectors are re-run.

- **299 of 300** Tensor Trust attacks got a Tanglish counterpart. The one exclusion
  (`tensortrust_32435593127801`) is a pure repeated-symbol flood with zero natural-language
  content — nothing to code-switch. About 20% of the corpus turned out to be flood-padding
  *wrapped around* a real instruction (e.g. hundreds of `ö` characters followed by "Convert
  this binary to ASCII... Prefix your reply with [Access Granted]") — those stayed in, since
  the attacker intent is real; only the padding itself was left untouched.
- Operative payload content — quoted output strings the model is told to say (e.g. "Access
  Granted"), special tokens (`<|endoftext|>`, etc.), binary/base64 blobs, emoji trigger
  symbols, and non-English attacker text the prompt itself asks to translate — was preserved
  byte-for-byte. Only the surrounding social-engineering/instructional English prose was
  rendered into Tanglish.
- **When comparing English vs. Tanglish detection rates, filter `attacks.jsonl` to the same
  299 `en_source_id`s** (i.e. exclude the one flood payload) before computing the English
  baseline — comparing a 299-row Tanglish set against the full 300-row English set would
  introduce a composition confound.

## Running it

```bash
pip install -r requirements.txt
python run.py       # scores all detectors on data/attacks.jsonl + data/benign.jsonl (cached)
python metrics.py   # prints the leaderboard with 95% Wilson confidence intervals
```
