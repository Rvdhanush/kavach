# CLAUDE.md — Kavach (guardrail robustness benchmark)

> Concise session context. The full brief is in **SPEC.md** — read it before making
> any design or scope decision.

## What this project is
An independent, reproducible benchmark that measures how well existing LLM safety
guardrails (prompt-injection / jailbreak **detectors**) actually catch attacks — and
whether they fail when the same attack is written in code-switched Hindi/Tamil.

This is **defensive security research**: we evaluate defenses, we do not build attacks.

## Critical distinctions — never conflate these
- **Detectors are what we score.** Meta Prompt Guard, ProtectAI DeBERTa, LLM Guard,
  Llama Guard, an LLM-as-judge. The leaderboard ranks *detectors*.
- **Datasets are ammunition, not subjects.** Tensor Trust, HackAPrompt, BIPIA supply the
  attack payloads we fire *at* the detectors. We never "rate a dataset."
- **Code-switching is a finding, not a feature.** We are not helping anyone write Hinglish.
  We are proving detectors *fail* on code-switched attacks. It is a test dimension.
- **The playground exposes blind spots.** A user pastes their system prompt, picks a
  language, and sees which detectors let an attack through. We do not score their prompt.

## Scope discipline (important)
- **Phase 1 = English only.** Build the harness, fire English attacks, score detectors,
  publish the leaderboard. Ship this first, finished and small.
- **Do NOT build in Phase 1:** code-switched attacks, the live playground, extra languages,
  or any defense/mitigation model. Those are later phases.
- Build order: **English benchmark → code-switch finding (Phase 2) → extensions.**

## Metrics — always report BOTH
- **Detection rate** — of real attacks, the fraction correctly flagged (recall on attacks).
- **Over-defense (false-positive rate)** — of *benign* inputs, the fraction wrongly flagged.
- A detector that flags everything scores 100% detection and is useless. Both are mandatory.

## Architecture rules
- **Adapter pattern is mandatory.** Every detector implements one interface:
  `predict(text) -> {"flagged": bool, "score": float}`. Adding a detector = one new file.
- Pipeline: `data/ → detectors/ (adapters) → run.py → metrics.py → results/`.
- **Cache** each `(payload × detector)` result; never re-run the same call.
- **Config-driven**: a config file lists which detectors and datasets a run uses.
- Keep it a plain Python package. No heavy frameworks. **No paid-API dependency** —
  start with free, local detectors.

## Conventions
- Python 3.11+. Attack/benign data as JSONL. Metrics via scikit-learn.
- Payloads come only from public, citable datasets — **never hand-write attack strings.**
- Detector adapters stay thin and uniform; all logic differences live inside the adapter.

## Commands
- Install: `pip install -r requirements.txt`
- Run a benchmark: `python run.py`
