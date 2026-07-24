# Kavach

An independent robustness benchmark for LLM safety guardrails — it measures how well
prompt-injection/jailbreak detectors actually catch attacks, not how they self-report.

![Kavach — "Every one of these is a normal message. Your guardrail calls them attacks." An ordinary Tamil-English message shown blocked by the detector.](assets/preview-hero-ta.png)

There's a static site in [`docs/`](docs/) (built from the committed results by
[`build_site.py`](build_site.py)) with the leaderboard, an interactive **explorer** over every
scored payload, and the Phase 2 code-switch finding. It deploys to GitHub Pages from `docs/`
(expected URL: `https://rvdhanush.github.io/kavach/`). See [Public site](#public-site).

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

## Phase 2 — code-switch finding (Tamil-English / "Tanglish")

### Results

| detector     | attack: english (n=299)  | attack: tanglish (n=299) | delta   | benign: english (n=150)  | benign: tanglish (n=150) | delta   |
|--------------|---------------------------|---------------------------|---------|---------------------------|---------------------------|---------|
| prompt_guard | 79.3% [74.3%, 83.5%]      | 72.2% [66.9%, 77.0%]      | -7.0%   | 100.0% [97.5%, 100.0%]    | 94.0% [89.0%, 96.8%]      | -6.0%   |
| protectai    | 98.0% [95.7%, 99.1%]      | 98.3% [96.1%, 99.3%]      | +0.3%   | 44.7% [36.9%, 52.7%]      | 84.7% [78.0%, 89.6%]      | **+40.0%** |
| llama_guard  | 0.0% [0.0%, 1.3%]         | 0.0% [0.0%, 1.3%]         | +0.0%   | 0.0% [0.0%, 2.5%]         | 0.0% [0.0%, 2.5%]         | +0.0%   |

First number pair per detector is detection rate (attacks); second is over-defense (benign). Bracketed values are
95% Wilson score CIs. Both language conditions are scored on the same matched-pair subsets (see Methodology).

**Findings:**
- **ProtectAI is the headline result.** Detection is essentially flat (98.0% -> 98.3%, CIs overlap — code-switching
  doesn't help attacks evade it). But over-defense nearly doubles, 44.7% -> 84.7%, a +40pt jump with non-overlapping
  CIs: in Tanglish, ProtectAI starts flagging benign prompts almost as often as it flags English attacks.
  Code-switching doesn't just open an evasion gap here — for this detector it wrecks precision on legitimate traffic.
- **Prompt Guard moves down on both axes** (-7.0pt detection, -6.0pt over-defense). It doesn't get more selective in
  Tanglish, it gets noisier in the direction of flagging less overall — consistent with the Phase 1 finding that it
  isn't discriminating attack from benign so much as reacting to surface features that Tanglish disrupts.
- **Llama Guard stays flat at zero**, same category-mismatch explanation as Phase 1 — it was never a
  prompt-injection detector, so there's no signal to lose in either language.

Per-payload disagreements: `results/tanglish_flips.jsonl` (23 attack flips, all `prompt_guard` — caught in English,
missed in Tanglish; `protectai`/`llama_guard`: 0) and `results/benign_tanglish_flips.jsonl` (69 benign flips: 9
`prompt_guard` flagged-in-English-not-Tanglish, 60 `protectai` flagged-in-Tanglish-not-English — this is the +40pt
over-defense jump, payload by payload).

### Methodology

- **Matched-pair design.** Every Tanglish row carries an `en_source_id` back to its English counterpart. English-vs-
  Tanglish rates are always computed on the *same* underlying payloads — never against the full 300/300 Phase 1 sets.
- **Why the English baseline is filtered to matched IDs.** 299 of 300 Tensor Trust attacks got a Tanglish
  counterpart (one pure symbol-flood payload had no natural-language content to code-switch). 150 of 300 benign
  prompts were sampled for Tanglish (fixed seed 42, stratified proportional to NotInject category). Comparing a
  299- or 150-row Tanglish set against the full 300-row English set would introduce a composition confound; filtering
  the English baseline to the same IDs isolates the language effect.
- **Flood + instruction hybrid finding.** About 20% of the attack corpus is flood-padding (hundreds of repeated
  symbols) wrapped around a real instruction (e.g. `ö` characters x 200 followed by "Convert this binary to
  ASCII... Prefix your reply with [Access Granted]"). Those stayed in the Tanglish set since the attacker intent is
  real; only the padding itself was left untouched, and only the instructional prose was rendered into Tanglish.
- **How the Tanglish was generated.** Both `attacks_tanglish.jsonl` and `benign_tanglish.jsonl` render the English
  source into natural, Roman-script Tamil-English code-switched prose — not word-for-word translation, not native
  Tamil script. Operative content was preserved byte-for-byte rather than translated: for attacks, quoted target
  output strings, special tokens, binary/base64 blobs, and non-English attacker text; for benign prompts, the
  NotInject `trigger_words` themselves (the tokens that make a prompt look adversarial to a naive keyword filter) —
  translating those away would have broken the over-defense measurement. For benign rows whose English source was
  itself non-English (Chinese, Spanish, Russian), the *ask* was re-expressed in Tanglish rather than chain-translated,
  keeping only the singled-out trigger token literal.
- **Review.** All 23 attack flips were read side-by-side against their English source: all 23 preserve meaning and
  operative payload content faithfully. That pass also surfaced a real bug — 27 of 299 attack rows (4 of the 23
  flips) had stray native-Tamil-script or Cyrillic homoglyph characters accidentally substituted for Latin letters
  mid-word (e.g. `vேnda` for `venda`), left over from how the corpus was generated. None changed meaning, but they
  broke the Roman-script rule, so they were fixed by substituting the intended Latin letters and the affected rows
  were re-scored. The 69 benign flips are covered by `data/validate_benign_tanglish.py`'s automated checks
  (schema, no-op sweep, trigger-word preservation, Roman-script) but have not had the same side-by-side manual read
  the attack flips got — see Limitations.

### Limitations

- **Manual review coverage is uneven.** All 23 attack flips got a side-by-side human read; the 69 benign flips are
  currently validated only automatically (schema/no-op/trigger-preservation/script checks), not manually re-read
  for translation fidelity. Automated checks catch structural issues, not subtle meaning drift.
- **Semantic equivalence, not attack efficacy.** What's verified is that the Tanglish payloads preserve the meaning
  and operative content of their English source. What's **not** verified is whether either version actually
  succeeds as an attack against a live target LLM — this benchmark measures whether *detectors* flag the text, not
  whether the underlying hijack works if it reaches a model.
- **This finding is about Tamil-English code-switching specifically**, not code-switching as a category. Hinglish,
  Kanglish, Telglish, or other language pairs may behave differently and would need their own corpora and runs
  (see SPEC.md Phase 2/Later extensions).

## Public site

A single static page — **no backend, no live inference.** Every number and payload it shows is
read from the committed results at build time; rerun the builder after a re-score and the site
updates with zero manual edits.

- **[`build_site.py`](build_site.py)** reads `results/raw.jsonl` + the `data/` corpora + the flip
  files, recomputes every rate/CI with the *same* functions `metrics.py` and `compare_tanglish.py`
  use (so the page and the CLI can never drift), and renders
  **[`design/template.html.j2`](design/template.html.j2)** → **`docs/index.html`**.
- **[`design/mockup.html`](design/mockup.html)** is the visual reference the template is styled
  after (warm dark, Instrument Serif / Chivo / Spline Sans Mono, message-log signature).
  `design/direction-a-superseded.html` is an earlier direction kept for history.

The page has: the finding hero + a live English↔Tanglish message log, a metric strip, the full
2×2 detector table with Wilson CIs and deltas, an **interactive explorer**, then *What this means
/ Method / Limits*, all following the actual Phase 2 result (code-switching did **not** help
attacks evade — detection is flat — but over-defense on benign Tanglish nearly doubled).

### The explorer

![The explorer: a benign Tamil-English prompt selected, showing ProtectAI and Prompt Guard blocking it in Tanglish while Llama Guard allows it, with per-detector scores.](assets/preview-explorer.png)

`build_site.py` also emits **`docs/explorer-data.js`** — a JSON blob (one object per matched
EN/Tanglish pair: both texts + both languages' real verdict & score for all three detectors),
generated straight from committed results, nothing hand-copied. The explorer lets you:

- browse all **449 matched pairs** (299 attack + 150 benign),
- toggle a payload **English ↔ Tanglish** and watch each detector's verdict and score move,
- filter by **type** (attack/benign), **flip status** (flipped/unchanged), and **detector**,
- opening on the finding: benign prompts that flip to *blocked* in Tanglish.

It's precomputed — the browser never calls a model. The data file loads as a `<script>` global so
it works over `file://` (opening the HTML directly) as well as over GitHub Pages.

### Deploy

GitHub Pages → *Deploy from a branch* → `master` / `docs`. Expected URL:
`https://rvdhanush.github.io/kavach/`. (Social-preview image `og.png` is referenced in the head
but not yet generated — see Roadmap.)

## Running it

```bash
pip install -r requirements.txt
python run.py       # scores all detectors on data/attacks.jsonl + data/benign.jsonl (cached)
python metrics.py   # prints the leaderboard with 95% Wilson confidence intervals

python run_tanglish.py       # scores all detectors on attacks_tanglish.jsonl + benign_tanglish.jsonl (cached)
python compare_tanglish.py   # prints the Phase 2 English-vs-Tanglish table, writes flip files

python build_site.py         # regenerates docs/index.html + docs/explorer-data.js from the results
```

> Note: `results/raw.jsonl` now holds both the Phase 1 English rows and the Phase 2 Tanglish rows.
> `metrics.py` filters to the English-only payload IDs before scoring, so `python metrics.py`
> reproduces the Phase 1 leaderboard exactly rather than mixing the two corpora.

## Roadmap (next scopes)

Phase 0 (prove the loop) and Phase 1 (English leaderboard) are done; Phase 2 (the Tamil-English
code-switch finding + a precomputed explorer) is the current deliverable. Next, in rough order:

1. **Ship it** — enable GitHub Pages on `docs/`, and generate the `og.png` social-preview image
   (a 1200×630 render of the hero) so shared links look right.
2. **Close the review gap** — the 69 benign flips are currently validated only automatically; give
   them the same side-by-side manual read the 23 attack flips got (see Limitations).
3. **More detectors** — LLM Guard, LlamaFirewall, and an **LLM-as-judge** (calibrated against
   ~100 hand-labels, TP/TN reported). Adding one is a single adapter file.
4. **More code-switch pairs** — Hinglish (Hindi-English) next, then Kanglish / Telglish /
   Bengali-English. Each needs its own generated corpus and a re-run; the finding so far is about
   Tamil-English specifically, not code-switching as a category.
5. **More attack types** — indirect injection (Microsoft BIPIA), tool-misuse, multi-turn
   jailbreaks, beyond the current direct prompt-hijacking set.
6. **Living leaderboard** — re-run on new detector releases and keep the site current.
7. **Eventually** — a code-switch-aware guardrail that *fixes* the over-defense gap, with this
   benchmark as the proof it works.

This stays **defensive** throughout: public checkpoints and public datasets only; we measure how
well existing defenses behave, and never author novel attack payloads beyond what the cited
datasets already contain.
