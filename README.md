# minga-prompt-audit

**An audit skill for Claude prompts and skills: outdated techniques, conflicts, dead references and bloat — reported line by line with a ready-to-apply diff.**

Part of the [Minga](https://github.com/dmminga1983/minga) ecosystem. The skill checks `CLAUDE.md`, `AGENTS.md`, `SKILL.md`, rules, commands, subagents and system prompts for patterns that hold modern Claude models back: ALL-CAPS pressure, forced reasoning scaffolds, rules that contradict each other, references to files that don't exist, duplicates. Nothing in your files changes until you say "apply".

[Русская версия →](README.ru.md)

## How it differs from the built-in `prompt-audit`

| | `/claude-api prompt-audit`, `/doctor prompt-audit` | minga-prompt-audit |
|---|---|---|
| Where it runs | Claude Code CLI | claude.ai, Claude Code, any agent that supports skills |
| Check catalogue | not published | open, with IDs and examples ([checks/](checks/)) |
| Russian text | — | Russian pressure and persona patterns; abbreviations such as ГОСТ, СП, ЖК are not treated as caps |
| Deterministic scanner | — | `scripts/scan.py`, no dependencies, with tests |
| Protected lines | keep-list | `<!-- keep -->` and `<!-- keep:start -->…<!-- keep:end -->` blocks |

## What it checks (v1.0)

| Block | Checks |
|---|---|
| **A. Outdated techniques** | A1 caps pressure · A2 threats and rewards · A3 "think step by step" · A4 empty persona · A5 repeating a rule "to be safe" · A6 absolutes without a reason · A7 prohibitions only |
| **B. Conflicts** | B1 within a file · B2 across files · B3 format/language · B4 unclear priority |
| **C. Dead references** | C1 files and `@imports` · C2 commands and scripts · C3 tools and skills · C4 outdated model names |
| **D. Bloat** | D1 duplicates · D2 long examples · D3 the obvious · D4 oversized files |

Detailed criteria are in [checks/](checks/) (in Russian), before/after examples in [examples/](examples/before-after.md).

**Coming in 1.1:** E — SKILL.md structure and `description` quality, F — security (secrets in prompts, prompt injection in tool descriptions), G — clarity (success criteria and output format), H — skill triggering.

## Install

**claude.ai** — on the repository page click *Code → Download ZIP* and upload the archive in *Settings → Capabilities → Skills*.

**Claude Code** — clone into your skills folder:

```bash
git clone https://github.com/dmminga1983/minga-prompt-audit ~/.claude/skills/minga-prompt-audit
```

## Usage

Just ask:

> Audit my CLAUDE.md and skills for outdated prompting

> Run an audit on `.claude/skills/report`

> Проверь мой CLAUDE.md и скиллы на устаревшие промпты

The report is grouped by severity — 🔴 critical · 🟠 important · ⚪ cosmetic — with file, line and quote for every finding, followed by one combined diff. Reply "apply all" or list the IDs to apply.

### Scanner on its own

```bash
python3 scripts/scan.py                        # CLAUDE.md, AGENTS.md, SKILL.md and .claude/ in the current folder
python3 scripts/scan.py .claude/skills/report  # a specific folder
python3 scripts/scan.py --home --format json   # also ~/.claude, JSON output
```

The scanner catches mechanical issues (blocks A, C, D). Conflicts (B) and judgement-based checks are done by the model following the skill.

### Protecting lines from the audit

```markdown
Leave this line alone <!-- keep -->

<!-- keep:start -->
THIS WHOLE BLOCK STAYS AS IS
<!-- keep:end -->
```

## Development

```bash
python3 -m unittest discover -s tests -v
```

Python 3.8+ only, no external dependencies.

## License

[MIT](LICENSE). The check catalogue is original work and does not copy Anthropic's internal guides.
