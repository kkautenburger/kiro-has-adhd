# Eval

Two layers, both scoped to the 10 rules in `../skills/kiro-has-adhd/SKILL.md`.

## 1. Deterministic gate — `check_rules.py`

No model, no network, no key. Runs in CI on every change to the skill. Catches the objective violations a regex can see:

| Check | Rule | What it flags |
| --- | --- | --- |
| R1/R10 | 1, 10 | First non-empty line opens with a preamble ("Great question", "Let me…") |
| R10 | 10 | Closing pleasantry near the end ("Hope this helps", "Let me know if…") |
| R6 | 6 | Talks about duration with vague wording and no concrete time unit |
| R9 | 9 | A list with more than 5 consecutive items |

Run it:

```bash
uv run evals/check_rules.py self-test          # prove the checker catches seeded violations
uv run evals/check_rules.py validate           # check cases.jsonl parses
echo "Great question! Let me help." | uv run evals/check_rules.py score   # score any text
uv run evals/check_rules.py score --text "Run \`npm test\`. Next: paste the failure."
```

Exit 0 = pass, exit 1 = violation. This is the CI gate.

Note: R1's regex only sees preamble openers; it does not prove the first line is a genuinely useful action. Rules 2, 3, 4, 5, 7, 8 are semantic and are left to the LLM judge below. The deterministic gate is a floor, not the whole rubric.

## 2. Optional LLM judge — `judge.py`

Higher-fidelity paired eval: each prompt in `cases.jsonl` runs twice — baseline (model without the skill) vs candidate (model with the skill) — then the model judges each output 0–10 on the 10 rules. Applies a release gate: candidate mean must beat baseline by `--min-delta`.

Gated on a provider key. With no `OPENAI_API_KEY` it prints a skip notice and exits 0, so CI never fails for lack of a secret.

```bash
uv run evals/judge.py --dry-run                # plan only, no network
OPENAI_API_KEY=sk-... uv run evals/judge.py --trials 3 --min-delta 1.0
```

Record runner/model/cases/trials/rubric/gate when you report a run.

## Cases — `cases.jsonl`

One JSON object per line: `id`, `prompt`, `rules` (which rules it exercises), `note`. Kiro-shaped prompts (fix a bug, multi-step setup, "what are my options", "how long", explain-mode). Add a case whenever you add or change a rule.

## When this runs

- CI (`.github/workflows/eval.yml`) runs the deterministic gate on any push/PR that touches `skills/**/SKILL.md` or `evals/**`.
- The LLM judge runs in the same workflow only if an `OPENAI_API_KEY` secret is configured; otherwise it skips.
