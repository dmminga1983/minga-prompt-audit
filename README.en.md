# minga-prompt-audit

**An audit skill for Claude prompts and skills: outdated techniques, conflicts, dead references and bloat — reported line by line with a ready-to-apply diff.**

[Русский](README.md) · Part of the [Minga](https://github.com/dmminga1983/minga) ecosystem

It checks `CLAUDE.md`, `AGENTS.md`, `SKILL.md`, rules, commands, subagents and system prompts for patterns that hold modern Claude models back: ALL-CAPS pressure, forced reasoning scaffolds, rules that contradict each other, references to files that don't exist, duplicates. Nothing changes until you say "apply".

## Checks (v1.0)

| Block | Checks |
|---|---|
| **A. Outdated techniques** | A1 caps pressure · A2 threats/rewards · A3 "think step by step" · A4 empty persona · A5 repetition · A6 unexplained absolutes · A7 prohibitions only |
| **B. Conflicts** | B1 within a file · B2 across files · B3 format/language · B4 unclear priority |
| **C. Dead references** | C1 files and `@imports` · C2 commands/scripts · C3 tools/skills · C4 outdated model names |
| **D. Bloat** | D1 duplicates · D2 long examples · D3 the obvious · D4 oversized files |

Coming in 1.1: E — SKILL.md structure, F — security, G — clarity, H — skill triggering.

Works with Russian and English text. Details: [checks/](checks/), examples: [examples/](examples/before-after.md).

## Install

- **claude.ai:** click *Code → Download ZIP* on the repo page and upload the archive in *Settings → Capabilities → Skills*.
- **Claude Code:** `git clone https://github.com/dmminga1983/minga-prompt-audit ~/.claude/skills/minga-prompt-audit`

## Use

> Audit my CLAUDE.md and skills for outdated prompting

Standalone scanner (Python 3.8+, no dependencies):

```bash
python3 scripts/scan.py [paths] [--home] [--format md|json]
```

Protect lines with `<!-- keep -->` or `<!-- keep:start -->…<!-- keep:end -->`.

## License

[MIT](LICENSE). The check catalogue is original work and does not copy Anthropic's internal guides.
