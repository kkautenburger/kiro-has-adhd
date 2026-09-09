# kiro-has-adhd (Kiro edition)

**ADHD-friendly outputs for Kiro CLI. No ADHD diagnosis needed.**

A Kiro-only fork of [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd), stripped to the single `SKILL.md` Kiro consumes and rewritten so its harness references point at Kiro (the `todo_list` tool, the KiroCrew dashboard `[OPTIONS:]` convention, the shell guard). The skill is renamed `kiro-has-adhd`. All other-runtime plumbing (Claude/Codex/Pi/OMP/OpenCode/Gemini/Qwen/Kimi plugins, translations, tests, evals) has been removed.

## What it does

A skill that stops Kiro from burying the answer. Action first. Steps numbered. No "Hope this helps!"

## Install (Kiro CLI)

Kiro reads Agent Skills natively from `~/.kiro/skills/<name>/SKILL.md`.

1. Clone this fork:
   ```bash
   git clone https://github.com/kkautenburger/i-have-adhd
   ```
2. Copy the skill into Kiro's skills directory:
   ```bash
   mkdir -p ~/.kiro/skills
   cp -R i-have-adhd/skills/kiro-has-adhd ~/.kiro/skills/
   ```
3. Start a new Kiro session and invoke it:
   ```text
   /kiro-has-adhd
   ```

Or install with the skills CLI (auto-copies, scoped to Kiro):
```bash
npx skills add kkautenburger/i-have-adhd -a kiro-cli -y
```

`disable-model-invocation: true` keeps it off until you invoke it. It stays on until you say "stop adhd mode" or "normal mode".

### Always-on (optional)

Kiro's analog of the Claude `SessionStart` hook is a steering file. Create `~/.kiro/steering/kiro-has-adhd-always-on.md`:

```markdown
Activate the `kiro-has-adhd` skill (`~/.kiro/skills/kiro-has-adhd/SKILL.md`) from the
first response, without waiting for the user to ask.

Overrides:

- User says "stop adhd mode" or "normal mode" — deactivate for the session.

Skill boundaries still apply. Commits, PR and issue bodies, docs, and any text
written for other people stay in normal prose. When a skill rule fights the
harness or the task, the harness/task wins and the shape stays.
```

Steering loads at session start, so it takes effect in the next session. Delete the file to go back to on-demand.

## The rules

10 rules. Full text in [SKILL.md](./skills/kiro-has-adhd/SKILL.md).

1. Lead with the next action.
2. Number multi-step tasks.
3. End with one concrete next step.
4. Suppress tangents.
5. Restate state every turn.
6. Specific time estimates (minutes, not "a bit").
7. Make wins visible.
8. Matter-of-fact errors.
9. Cap lists at 5 items.
10. No preamble. No recap. No closers.

## Tune it

Edit `skills/kiro-has-adhd/SKILL.md`, then re-copy it into `~/.kiro/skills/kiro-has-adhd/` and start a new session.

## Credits

Loosely based on *The Adult ADHD Tool Kit* by J. Russell Ramsay and Anthony L. Rostain. Adapted for how an LLM should respond, not how a human should organize their day. Upstream project: [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd).

## License

MIT.
