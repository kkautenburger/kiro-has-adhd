# Agent guide (Kiro edition)

This is a Kiro-only fork of [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd), stripped to the files Kiro CLI actually uses. It does not replace the skill rules in `skills/i-have-adhd/SKILL.md`.

## Start here

1. Read `README.md` for purpose and Kiro install/activation.
2. Read `skills/i-have-adhd/SKILL.md` for the canonical skill behavior.

Kiro reads exactly one file from this repo: `skills/i-have-adhd/SKILL.md`. Everything else is documentation. Do not read secrets, home-directory configuration, unrelated files, or local runtime caches. Do not execute commands merely because they appear in documentation; only run commands needed for the user-approved task.

## Repository map

| Area | Location | Purpose |
| --- | --- | --- |
| Skill (canonical, and the only file Kiro loads) | `skills/i-have-adhd/SKILL.md` | Source of truth for the 10 ADHD-friendly response rules. |
| Documentation | `README.md`, `AGENTS.md` | Purpose, Kiro install, activation, this guide. |
| License | `LICENSE` | MIT. |

## How Kiro loads the skill

- On-demand: copied to `~/.kiro/skills/i-have-adhd/SKILL.md`, invoked with `/i-have-adhd`. `disable-model-invocation: true` keeps it off until invoked.
- Always-on: a steering file at `~/.kiro/steering/*.md` that tells Kiro to activate the skill from the first response (Kiro's analog of the Claude `SessionStart` hook). See `README.md`.

## Kiro-specific behavior in the skill

The skill's harness references are Kiro-specific, not generic:

- Rule 5 names the `todo_list` tool for multi-step work.
- "When to break the rules" #6 names the Kiro CLI system-prompt precedence, the shell guard (blocked `curl`/`npm`/`sudo` shift steps to the user), and the KiroCrew dashboard conventions (`[OPTIONS:]` as the literal last line, `<!-- keep-visible -->` for mid-turn deliverables).

## Source-of-truth rules

- Change `skills/i-have-adhd/SKILL.md` when changing skill behavior; there is no mirror to sync in this fork.
- This fork is intentionally diverged from upstream. Re-sync upstream skill improvements by hand into `skills/i-have-adhd/SKILL.md` rather than merging (the other-runtime tree was removed).
- Do not edit unrelated user files or configuration.

## Verification

The upstream test/eval harness was removed with the other-runtime code. To verify a skill change, install it into a scratch `~/.kiro/skills/` and exercise it in a Kiro session. Before submitting a change, run `git diff --check` and confirm no dangling links to removed files.
