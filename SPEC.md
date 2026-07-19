# SPEC — Kavach: an independent robustness benchmark for LLM guardrails

## 1. One-line summary
A reproducible, open-source benchmark that measures how well leading LLM safety guardrails
(prompt-injection and jailbreak detectors) actually catch attacks — and reveals that they
fail badly when the attack is written in code-switched Hindi (Hinglish) or Tamil (Tanglish).

## 2. Thesis / why this exists
Prompt injection is the #1 unsolved LLM security problem, and essentially every detector is
trained and evaluated on English. Whether these detectors hold up on code-switched attacks
is an open question almost nobody has published. This project answers it with numbers.

The strategic point: we are **not** shipping the 31st guardrail product. We are the
**independent evaluator** of the crowded guardrail space. Crowding is an asset here — the
more detectors exist with only self-reported numbers, the more valuable a neutral benchmark.

This is defensive security research (robustness evaluation of defenses). It sits in an active
published area — "evasion attacks against guardrails" — where code-switching is a natural,
underexplored evasion vector.

## 3. Critical distinctions (do not conflate)
- **Detectors = what we score.** The leaderboard ranks detectors.
- **Datasets = ammunition.** They supply the attack payloads fired *at* detectors. Never rated.
- **Code-switching = a finding, not a user feature.** We prove detectors *fail* on it.
- **Playground = shows a user's guardrail blind spots**, not a score of their prompt.

## 4. Phases (strict order — each is independently shippable)

**Phase 0 — prove the loop (one weekend).**
One detector (Meta Prompt Guard), ~40 attacks from one dataset (Tensor Trust) + ~40 benign
inputs, a `run.py` that scores all of them, and the two metrics printing. That's it.

**Phase 1 — the English benchmark (GitHub, ships first).**
- 4–5 detectors behind the adapter interface.
- A few hundred attacks sampled from public datasets, plus a benign set.
- Score every detector on detection rate + over-defense.
- Publish a leaderboard (table + short methodology writeup). This is a complete artifact
  on its own — if momentum stops here, it's still a strong portfolio piece.

**Phase 2 — the code-switch finding + live demo (the differentiator).**
- Transliterate the same attacks into Hinglish and Tanglish.
- Re-run; show the detection-rate collapse per detector.
- Wrap it as the live "attack playground" (see design notes). This is the memorable part.

**Later — extensions (only after Phase 2):**
More detectors; more languages (Kanglish, Telglish, Bengali-English); more attack types
(indirect injection, tool-misuse, multi-turn jailbreaks); a living leaderboard updated on new
releases; and eventually a code-switch-aware guardrail that *fixes* the gap, with this
benchmark proving it works.

## 5. Detectors to evaluate (all free; start local)
Start with the two small classifiers (run on CPU, no paid key):
- **Meta Prompt Guard** — multilabel classifier (mDeBERTa-v3, ~86M), flags direct jailbreaks
  and indirect injections. HuggingFace.
- **ProtectAI DeBERTa v2** — fine-tuned deberta-v3-base (~184M) injection detector. HuggingFace.
  Note: v2 is not trained on jailbreaks — report that limitation as a finding.

Then add breadth:
- **LLM Guard** — leading open-source runtime guard with an injection scanner; self-hosted.
- **Llama Guard / LlamaFirewall** — Meta's open guardrail model.
- **LLM-as-judge** — prompt a base model to classify "is this an injection attempt." This is
  the bridge to Phase 2 and where calibration rigor shows (see §7).
- (Optional, heavier) **NVIDIA Garak** — probe-based red-team scanner; add last.

## 6. Attack payloads — from public datasets only
Do not hand-write attacks. Use standardized, citable corpora (reproducible + comparable):
- **Tensor Trust** — 563K+ interpretable prompt-injection attacks (ICLR 2024). Primary source
  for direct injection.
- **HackAPrompt** — large public dataset from the injection competition.
- **Microsoft BIPIA** — indirect injection across several tasks (for later phases).
- HuggingFace jailbreak-prompt datasets — jailbreak coverage.
Sample a few hundred to start; the full corpora are not needed for a first benchmark.

A **benign set** is required too (normal instructions that look adversarial) to measure
over-defense — see NotInject / InjecGuard for the over-defense framing.

## 7. Metrics (report both, always)
- **Detection rate** = fraction of real attacks flagged (recall on the attack set).
- **Over-defense / false-positive rate** = fraction of benign inputs wrongly flagged.
- For the LLM-as-judge specifically: calibrate it. Hand-label ~100 cases, measure the judge's
  agreement (true-positive / true-negative rates) against those labels, and report it. An
  uncalibrated judge is the most common eval failure — doing this right is itself a signal.
- Where possible, prefer a checkable outcome ("did the model follow the injected instruction —
  yes/no") over fuzzy quality judgments, which is easier to score reliably.

## 8. Architecture
Deliberately simple — a batch pipeline. The one load-bearing decision is the adapter pattern.

```
kavach/
  data/
    attacks.jsonl        # sampled from public datasets; tag source + attack_type + language
    benign.jsonl         # benign-but-tricky inputs, for over-defense
  detectors/
    base.py              # interface: predict(text) -> {"flagged": bool, "score": float}
    prompt_guard.py      # one thin adapter per detector
    protectai.py
    llm_guard.py
    llm_judge.py
  run.py                 # loops over (detector x sample), writes raw results (with caching)
  metrics.py             # detection rate + over-defense per detector
  configs/
    phase1.yaml          # which detectors + datasets a run uses
  results/               # raw outputs + computed leaderboard
```

Rules:
- Every detector implements the same `predict()` interface → adding one is a single file.
- Cache each `(payload, detector)` result so runs are never repeated.
- Runs are config-driven and reproducible.
- No heavy frameworks; no paid-API dependency in Phase 1.
- The eventual live playground is a thin web layer (FastAPI + the static frontend) that calls
  the *same* adapters — no duplicated detection logic.

Stack: Python 3.11+, HuggingFace transformers (local classifiers), scikit-learn (metrics),
JSONL data. Frontend later: the single-file HTML mockup, deployable to Vercel/Netlify.

## 9. Design notes (for the frontend, Phase 2+)
Aesthetic: clean developer-tool register (Supermemory/Vercel-class), reproduced via —
- **Two accent colors that carry meaning**: teal = "held/blocked", coral = "slipped through".
  Color encodes the finding; it is not decoration.
- **Monospace display font** (IBM Plex Mono + Plex Sans) for the engineering-instrument feel.
- **Hero = the finding**, not a generic tagline.
- **Leaderboard is the centerpiece**, tabular numbers so it reads as trustworthy.
- Signature element: a bilingual attack card — same payload, blocked in English, passed when
  code-switched — that tells the whole thesis in one interaction.
(A working mockup exists as a standalone HTML file.)

## 10. Guardrails on the work itself
- Public checkpoints, public datasets only.
- Defensive framing throughout: we measure how well defenses catch attacks.
- Never include operational/novel attack payloads in the repo beyond what public datasets
  already contain.
- Free/local detectors first so the project never depends on paid access.

## 11. What "done" looks like for the CV
"Built an independent robustness benchmark for LLM safety guardrails; found that leading
prompt-injection detectors fail significantly on code-switched (Hinglish/Tanglish) attacks —
a gap not addressed by existing tools. Open-source harness + live demo."
