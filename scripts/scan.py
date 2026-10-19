#!/usr/bin/env python3
"""minga-prompt-audit scanner — механические проверки блоков A, C, D.

Только стандартная библиотека Python 3.8+. Ничего не отправляет в сеть
и не меняет файлы. Вывод — черновик для ручной перепроверки моделью.

Использование:
    python3 scan.py [ПУТИ...] [--root DIR] [--format md|json] [--home]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

VERSION = "1.0.0"

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
INSTRUCTION_NAMES = {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "SKILL.md"}

# Аббревиатуры и термины, которые законно пишутся заглавными.
CAPS_ALLOW = {
    "API", "JSON", "YAML", "HTML", "HTTP", "HTTPS", "REST", "SQL", "CSV", "XML",
    "TODO", "FIXME", "NOTE", "README", "LICENSE", "CHANGELOG", "CLAUDE", "AGENTS",
    "SKILL", "URL", "UUID", "UTF", "ASCII", "PDF", "DOCX", "XLSX", "PPTX", "MCP",
    "CLI", "SDK", "LLM", "UI", "UX", "CI", "CD", "PR", "AWS", "GCP", "SSH", "GPG",
    "OAUTH", "JWT", "CORS", "DNS", "TLS", "SSL", "IDE", "ENV", "PATH", "HOME",
    "ГОСТ", "СНИП", "СП", "ООО", "ЗАО", "ПАО", "ИНН", "ОГРН", "КЕО", "ЖК", "СТЭ",
    "РФ", "ГК", "ДДУ", "МКД", "ЖКХ", "ТЗ", "ПО", "ИИ",
}

RE_CAPS_WORD = re.compile(r"(?<![\w$])([A-ZА-ЯЁ][A-ZА-ЯЁ]{3,})(?![\w])")
RE_BANG = re.compile(r"!{2,}")
RE_INLINE_CODE = re.compile(r"`[^`]*`")

RE_PRESSURE = re.compile(
    r"(уволят|увольн|чаевые|дам тебе \$|заплачу тебе|вопрос жизни и смерти|"
    r"от этого зависит (моя|мо[её] карьер|чья-то|жизнь)|накажу тебя|"
    r"\btip you\b|\$\d+ tip|i will tip|lose my job|you will be (penali[sz]ed|punished)|"
    r"life or death|my career depends|i'?ll be fired)",
    re.IGNORECASE,
)
RE_SCAFFOLD = re.compile(
    r"(думай (пошагово|шаг за шагом)|рассуждай (пошагово|шаг за шагом)|"
    r"давай подумаем шаг|think step[- ]by[- ]step|let'?s think|"
    r"write (your|out) (reasoning|thoughts) (first|before)|"
    r"сначала (распиши|напиши) (свои )?рассуждения|<thinking>)",
    re.IGNORECASE,
)
RE_ROLE = re.compile(
    r"((ты|you are|you're)\s+(—\s*)?(\w+\s+){0,4}"
    r"(эксперт|expert|senior|guru|гуру|профессионал|professional)\b.{0,80}?"
    r"(\d+[\s-]*(лет|летн|years?)|мирового уровня|world[- ]class))"
    r"|мирового уровня|world[- ]class",
    re.IGNORECASE,
)
RE_OLD_MODEL = re.compile(
    r"\bclaude[- ](instant|2(\.\d)?|3(\.5|\.7)?[- ](opus|sonnet|haiku)|3-5-(sonnet|haiku)|3-7-sonnet)\b",
    re.IGNORECASE,
)

RE_IMPORT = re.compile(r"(?<![\w`])@(~?[\w.\-/]*[\w\-]+(?:\.\w+|/))")
RE_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
PATH_EXTS = (".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
             ".sh", ".txt", ".toml", ".cfg", ".ini", ".sql", ".css", ".html")

FENCE = re.compile(r"^\s*(```|~~~)")
KEEP_LINE = "<!-- keep -->"
KEEP_START = "<!-- keep:start -->"
KEEP_END = "<!-- keep:end -->"

LONG_EXAMPLE = 40
SIZE_LIMITS = {"CLAUDE.md": 300, "CLAUDE.local.md": 300, "AGENTS.md": 300, "SKILL.md": 500}
DEFAULT_SIZE_LIMIT = 500


@dataclass
class Finding:
    id: str
    severity: str  # critical | important | cosmetic
    file: str
    line: int
    quote: str
    message: str


@dataclass
class Line:
    no: int
    text: str
    code: bool
    keep: bool


def parse(text: str) -> tuple[list[Line], int, list[tuple[int, int]]]:
    """Размечает строки: внутри блока кода / под keep. Возвращает строки,
    число защищённых строк и диапазоны блоков кода (начало, длина)."""
    lines, in_code, in_keep, kept = [], False, False, 0
    blocks, block_start = [], 0
    for i, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if KEEP_START in stripped:
            in_keep = True
        is_keep = in_keep or KEEP_LINE in raw
        if FENCE.match(raw):
            if in_code:
                blocks.append((block_start, i - block_start - 1))
            else:
                block_start = i
            in_code = not in_code
            lines.append(Line(i, raw, True, is_keep))
        else:
            lines.append(Line(i, raw, in_code, is_keep))
        if is_keep:
            kept += 1
        if KEEP_END in stripped:
            in_keep = False
    return lines, kept, blocks


def norm(s: str) -> str:
    s = re.sub(r"[`*_>#\-–—•|\d.)(\[\]!?:;,\"'«»]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def short(s: str, n: int = 140) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def looks_like_path(p: str) -> bool:
    if not p or any(c in p for c in "<>{}*$|") or "://" in p or p.startswith(("#", "mailto:")):
        return False
    if " " in p or p.startswith(("@", "[")) or "path/to" in p:
        return False
    return "/" in p or p.lower().endswith(PATH_EXTS)


def path_exists(ref: str, base: Path, root: Path) -> bool:
    ref = ref.split("#")[0].rstrip(".,;:")
    if not ref:
        return True
    if ref.startswith("~"):
        return Path(os.path.expanduser(ref)).exists()
    p = Path(ref)
    if p.is_absolute():
        return p.exists()
    return (base / p).exists() or (root / p).exists()


def scan_file(path: Path, root: Path, display: str) -> tuple[list[Finding], int, int, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines, kept, blocks = parse(text)
    out: list[Finding] = []
    norms: dict = {}

    def add(fid, sev, ln, msg):
        out.append(Finding(fid, sev, display, ln.no, short(ln.text), msg))

    for ln in lines:
        if ln.keep or ln.code:
            continue
        prose = RE_INLINE_CODE.sub(" ", ln.text)

        caps = [w for w in RE_CAPS_WORD.findall(prose) if w.upper() not in CAPS_ALLOW]
        if caps or RE_BANG.search(prose):
            what = ", ".join(dict.fromkeys(caps)) if caps else "«!!»"
            add("A1", "important", ln, f"Капс/восклицания ради давления: {what}")
        if RE_PRESSURE.search(prose):
            add("A2", "important", ln, "Угроза, награда или эмоциональный нажим")
        if RE_SCAFFOLD.search(ln.text):
            add("A3", "important", ln, "Принудительный шаблон рассуждений")
        if RE_ROLE.search(prose):
            add("A4", "cosmetic", ln, "Пустая роль «эксперт с N-летним опытом»")
        if RE_OLD_MODEL.search(ln.text):
            add("C4", "important", ln, "Упоминание устаревшей модели")

        # @-импорты и ссылки Markdown внутри `кода` не действуют — ищем только в прозе.
        refs = set(RE_IMPORT.findall(prose))
        refs |= {m for m in RE_MD_LINK.findall(prose) if looks_like_path(m)}
        # Пути в `кавычках`: только конкретные (a/b.ext, ./x) — голые имена вроде
        # `CLAUDE.md` или `rules/` обычно упоминаются как понятие, а не как файл.
        for m in RE_INLINE_CODE.findall(ln.text):
            c = m.strip("`").strip()
            if looks_like_path(c) and "/" in c.rstrip("/") and not c.startswith("~"):
                refs.add(c)
        for ref in sorted(refs):
            if not path_exists(ref, path.parent, root):
                add("C1", "critical", ln, f"Путь не найден: {ref}")

        n = norm(ln.text)
        if len(n) >= 25:
            norms.setdefault(n, []).append(ln)

    for start, length in blocks:
        if length > LONG_EXAMPLE:
            ln = next(l for l in lines if l.no == start)
            if not ln.keep:
                add("D2", "cosmetic", ln, f"Блок кода/пример на {length} строк (> {LONG_EXAMPLE})")

    limit = SIZE_LIMITS.get(path.name, DEFAULT_SIZE_LIMIT)
    if len(lines) > limit:
        out.append(Finding("D4", "important", display, 1, path.name,
                           f"Файл {len(lines)} строк (ориентир ≤ {limit}) — вынести детали в отдельные файлы"))
    return out, len(lines), kept, norms


def discover(paths: list[str], root: Path, home: bool) -> list[Path]:
    """Явно указанные папки — все .md внутри. Без аргументов — только
    файлы инструкций (CLAUDE.md, AGENTS.md, SKILL.md) и всё под .claude/."""
    targets: list[Path] = []
    explicit = bool(paths)
    if not explicit:
        paths = [str(root)]
        if home:
            paths.append(os.path.expanduser("~/.claude"))
    for p in paths:
        p = Path(os.path.expanduser(p))
        if p.is_file():
            targets.append(p)
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for f in filenames:
                    if not f.endswith(".md"):
                        continue
                    fp = Path(dirpath) / f
                    if explicit or f in INSTRUCTION_NAMES or ".claude" in fp.parts:
                        targets.append(fp)
    return sorted(dict.fromkeys(t.resolve() for t in targets))


def run(paths: list[str], root: Path, home: bool) -> dict:
    files = discover(paths, root, home)
    findings: list[Finding] = []
    total_lines = total_kept = 0
    all_norms: dict = {}
    for f in files:
        try:
            display = str(f.relative_to(root))
        except ValueError:
            display = str(f)
        fnd, n, kept, norms = scan_file(f, root, display)
        findings += fnd
        total_lines += n
        total_kept += kept
        for k, lns in norms.items():
            all_norms.setdefault(k, []).extend((display, l) for l in lns)

    for k, occ in all_norms.items():
        if len(occ) > 1:
            first_file, first = occ[0]
            where = ", ".join(f"{d}:{l.no}" for d, l in occ)
            findings.append(Finding("D1", "important", first_file, first.no, short(first.text),
                                    f"Повтор строки ({len(occ)} раза): {where}"))

    order = {"critical": 0, "important": 1, "cosmetic": 2}
    findings.sort(key=lambda x: (order[x.severity], x.file, x.line, x.id))
    return {
        "version": VERSION,
        "files": len(files),
        "lines": total_lines,
        "kept": total_kept,
        "findings": [asdict(f) for f in findings],
    }


SEV_TITLE = {"critical": "🔴 Критично", "important": "🟠 Важно", "cosmetic": "⚪ Косметика"}


def to_md(res: dict) -> str:
    f = res["findings"]
    cnt = {s: sum(1 for x in f if x["severity"] == s) for s in SEV_TITLE}
    out = [
        f"# Сканер minga-prompt-audit {res['version']} — черновик",
        "",
        f"Проверено: {res['files']} файлов, {res['lines']} строк. Защищено `keep`: {res['kept']} строк.",
        f"Итог: 🔴 {cnt['critical']} · 🟠 {cnt['important']} · ⚪ {cnt['cosmetic']}",
        "",
        "_Механические находки. Каждую перепроверить по контексту; блок B и смысловые проверки — вручную._",
    ]
    for sev, title in SEV_TITLE.items():
        items = [x for x in f if x["severity"] == sev]
        if not items:
            continue
        out += ["", f"## {title}"]
        for x in items:
            out.append(f"- **[{x['id']}]** `{x['file']}:{x['line']}` — {x['message']}  \n  > {x['quote']}")
    if not f:
        out += ["", "Механических проблем не найдено."]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="minga-prompt-audit scanner")
    ap.add_argument("paths", nargs="*", help="файлы или папки (по умолчанию — текущая папка)")
    ap.add_argument("--root", default=".", help="корень проекта для поиска путей")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--home", action="store_true", help="добавить ~/.claude при поиске по умолчанию")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args(argv)
    res = run(a.paths, Path(a.root).resolve(), a.home)
    if a.format == "json":
        json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(to_md(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
