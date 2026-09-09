#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx==0.28.*"]
# ///
"""Optional paired LLM-judge for the kiro-has-adhd skill.

Runs each prompt in evals/cases.jsonl twice against a chat model:
  baseline  = model WITHOUT the skill in its system prompt
  candidate = model WITH  skills/kiro-has-adhd/SKILL.md in its system prompt
then asks the same model, as an impartial judge, to score each output 0-10 on
adherence to the 10 ADHD rules. Reports mean baseline vs candidate and applies
a release gate: candidate mean must beat baseline by >= --min-delta.

This is the high-fidelity signal. It needs a provider key and costs tokens, so
it is INTENTIONALLY gated: with no key present it prints a skip notice and exits
0, so CI stays green without a secret. Provide one to actually run it:

  OPENAI_API_KEY   -> uses OpenAI chat completions
  (extend _complete() for other providers as needed)

Usage:
  uv run evals/judge.py --trials 1 --min-delta 1.0
  uv run evals/judge.py --dry-run          # no network; prints the plan

Never executes model output. Reads only repo-relative files.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "kiro-has-adhd" / "SKILL.md"
CASES = REPO / "evals" / "cases.jsonl"

JUDGE_SYSTEM = (
    "You are an impartial evaluator. Score how well a response follows these "
    "ADHD-friendly output rules, each 0-10, then give ONE overall 0-10:\n"
    "1 lead with the next action; 2 number multi-step tasks; 3 end with one "
    "concrete next action; 4 suppress tangents; 5 restate state; 6 concrete time "
    "estimates; 7 make wins visible; 8 matter-of-fact errors; 9 cap lists at 5; "
    "10 no preamble/recap/closer. Reply with STRICT JSON: {\"overall\": <int>, "
    "\"why\": \"<one sentence>\"}. Judge only structure, not correctness."
)


def load_cases() -> list[dict]:
    out = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _complete(system: str, user: str, model: str, key: str) -> str:
    import httpx

    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _judge_score(output: str, model: str, key: str) -> int:
    raw = _complete(JUDGE_SYSTEM, f"Response to score:\n\n{output}", model, key)
    try:
        return int(json.loads(raw)["overall"])
    except (json.JSONDecodeError, KeyError, ValueError):
        # be conservative: unparseable judge reply scores 0
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=os.environ.get("EVAL_MODEL", "gpt-4o-mini"))
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--min-delta", type=float, default=1.0,
                    help="candidate mean must exceed baseline mean by this much")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without any network call")
    args = ap.parse_args()

    if not SKILL.exists():
        print(f"skill not found at {SKILL}", file=sys.stderr)
        return 2
    cases = load_cases()

    if args.dry_run:
        print(f"[dry-run] model={args.model} trials={args.trials} "
              f"cases={len(cases)} min_delta={args.min_delta}")
        print(f"[dry-run] would run {len(cases) * args.trials * 2} completions "
              f"+ {len(cases) * args.trials * 2} judge calls")
        return 0

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("SKIP: no OPENAI_API_KEY in environment. The deterministic gate "
              "(check_rules.py) still ran; the LLM judge is optional and needs a "
              "provider key. Exiting 0 so CI stays green.")
        return 0

    skill_text = SKILL.read_text(encoding="utf-8")
    base_scores: list[int] = []
    cand_scores: list[int] = []

    for case in cases:
        for _ in range(args.trials):
            base_out = _complete("You are a helpful coding assistant.",
                                 case["prompt"], args.model, key)
            cand_out = _complete(
                "You are a helpful coding assistant.\n\n" + skill_text,
                case["prompt"], args.model, key)
            b = _judge_score(base_out, args.model, key)
            c = _judge_score(cand_out, args.model, key)
            base_scores.append(b)
            cand_scores.append(c)
            print(f"{case['id']:<14} baseline={b:>2}  candidate={c:>2}")

    bmean = sum(base_scores) / len(base_scores)
    cmean = sum(cand_scores) / len(cand_scores)
    delta = cmean - bmean
    print(f"\nbaseline mean={bmean:.2f}  candidate mean={cmean:.2f}  delta={delta:+.2f}")
    print(f"release gate: delta >= {args.min_delta} -> "
          f"{'PASS' if delta >= args.min_delta else 'FAIL'}")
    return 0 if delta >= args.min_delta else 1


if __name__ == "__main__":
    raise SystemExit(main())
