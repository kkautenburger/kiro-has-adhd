#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic ADHD-skill rule checker.

No model calls. Scores a single agent-response text against the mechanically
verifiable subset of the 10 rules in skills/kiro-has-adhd/SKILL.md. Used as the
CI gate that re-runs whenever SKILL.md changes: it validates that the *checker
itself* and the rule definitions stay coherent, and it can score any candidate
output text (piped in or via --text) for regression testing after a skill edit.

The full behavioral signal needs the LLM judge (see judge.py); this checker
catches the objective violations a regex can see:

  R1  lead with the next action  -> first non-empty line is not a hedge/preamble
  R6  specific time estimates    -> if the text talks duration, it uses units
  R9  cap lists at 5 items       -> no run of >5 consecutive list markers
  R10 no preamble / no closer     -> banned openers/closers absent

Exit 0 = all checked rules pass. Exit 1 = at least one violation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


PREAMBLE_OPENERS = [
    r"great question",
    r"let me\b",
    r"i'?ll\b",
    r"sure[!,. ]",
    r"looking at your",
    r"to answer your question",
    r"let'?s think about",
    r"let'?s dive",
    r"i'?d be happy to",
    r"certainly[!,. ]",
    r"of course[!,. ]",
]

CLOSERS = [
    r"let me know if you (need|have|want)",
    r"hope (this|that) helps",
    r"happy to (clarify|help)",
    r"feel free to (ask|reach)",
    r"anything else\??",
    r"don'?t hesitate to",
]

# Words that imply a duration claim; if present, we expect a concrete unit near one.
DURATION_TRIGGERS = re.compile(
    r"\b(take|takes|took|duration|how long|time to|timeline|effort|estimate|estimated)\b",
    re.IGNORECASE,
)
CONCRETE_TIME = re.compile(
    r"\b\d+\s*(second|sec|minute|min|hour|hr|day|week|month|afternoon|morning)s?\b"
    r"|\b(an?\s+(afternoon|hour|day|week))\b",
    re.IGNORECASE,
)
VAGUE_TIME = re.compile(
    r"\b(a bit|some (work|time)|a while|a few (moments)|not long|quick(ly)?|soon)\b",
    re.IGNORECASE,
)

LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")


@dataclass
class Result:
    passed: bool
    violations: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.violations.append(msg)


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_r1_action_first(text: str, r: Result) -> None:
    first = first_nonempty_line(text).lower()
    for pat in PREAMBLE_OPENERS:
        if re.match(rf"^\W*{pat}", first):
            r.fail(f"R1/R10: first line opens with a preamble: {first!r}")
            return


def check_r10_closer(text: str, r: Result) -> None:
    tail = "\n".join(text.strip().splitlines()[-3:]).lower()
    for pat in CLOSERS:
        if re.search(pat, tail):
            r.fail(f"R10: closing pleasantry near the end matches /{pat}/")
            return


def check_r6_time_units(text: str, r: Result) -> None:
    if DURATION_TRIGGERS.search(text):
        if VAGUE_TIME.search(text) and not CONCRETE_TIME.search(text):
            r.fail("R6: talks about duration with vague wording and no concrete unit")


def check_r9_list_cap(text: str, r: Result) -> None:
    run = 0
    max_run = 0
    for line in text.splitlines():
        if LIST_MARKER.match(line):
            run += 1
            max_run = max(max_run, run)
        elif line.strip() == "":
            continue
        else:
            run = 0
    if max_run > 5:
        r.fail(f"R9: a list has {max_run} consecutive items (>5)")


def score_text(text: str) -> Result:
    r = Result(passed=True)
    check_r1_action_first(text, r)
    check_r10_closer(text, r)
    check_r6_time_units(text, r)
    check_r9_list_cap(text, r)
    return r


# --- self-test fixtures: prove the checker catches what it should -------------

GOOD = (
    "Run `npm install jsonwebtoken`, then edit `src/auth.ts:42`.\n\n"
    "1. Open `src/auth.ts`\n2. Replace `verifyToken`\n3. Run the tests\n\n"
    "Next: paste the first failing line.\n"
)
BAD_PREAMBLE = "Great question! Let me think about this. Your auth flow has pieces.\n"
BAD_CLOSER = "Run the migration.\n\nHope this helps! Let me know if you need anything else.\n"
BAD_VAGUE_TIME = "This migration will take a bit of work, hard to say how long.\n"
BAD_LONG_LIST = "Do these:\n" + "".join(f"{i}. step {i}\n" for i in range(1, 8))


def self_test() -> int:
    cases = [
        ("good", GOOD, True),
        ("bad_preamble", BAD_PREAMBLE, False),
        ("bad_closer", BAD_CLOSER, False),
        ("bad_vague_time", BAD_VAGUE_TIME, False),
        ("bad_long_list", BAD_LONG_LIST, False),
    ]
    failures = 0
    for name, text, expect_pass in cases:
        res = score_text(text)
        ok = res.passed == expect_pass
        status = "OK" if ok else "SELFTEST-FAIL"
        print(f"[{status}] {name}: passed={res.passed} expected={expect_pass}"
              + ("" if not res.violations else f" :: {res.violations}"))
        if not ok:
            failures += 1
    if failures:
        print(f"\nself-test FAILED: {failures} case(s) behaved unexpectedly")
        return 1
    print("\nself-test OK: checker catches all seeded violations")
    return 0


def load_cases(path: str) -> int:
    """Validate the cases file parses and has required fields."""
    n = 0
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"cases.jsonl:{i}: invalid JSON: {e}")
                return 1
            for key in ("id", "prompt", "rules"):
                if key not in obj:
                    print(f"cases.jsonl:{i}: missing key {key!r}")
                    return 1
            n += 1
    print(f"cases.jsonl: {n} case(s) valid")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["self-test", "validate", "score"],
                    help="self-test: run seeded fixtures; validate: check cases.jsonl; "
                         "score: score --text or stdin")
    ap.add_argument("--text", help="candidate response text to score (score mode)")
    ap.add_argument("--cases", default="evals/cases.jsonl",
                    help="path to cases.jsonl (validate mode)")
    args = ap.parse_args()

    if args.command == "self-test":
        return self_test()
    if args.command == "validate":
        return load_cases(args.cases)
    # score
    text = args.text if args.text is not None else sys.stdin.read()
    res = score_text(text)
    if res.passed:
        print("PASS: no deterministic rule violations")
        return 0
    print("FAIL:")
    for v in res.violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
