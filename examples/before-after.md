# Примеры: до и после

<!-- keep:start -->

## Русский CLAUDE.md

**До**
```markdown
Ты эксперт мирового уровня с 20-летним опытом.
ОБЯЗАТЕЛЬНО запускай тесты!!! Если забудешь — меня уволят.
Думай пошагово и сначала распиши рассуждения.
Конфиг лежит в @docs/old-config.md
ОБЯЗАТЕЛЬНО запускай тесты!!!
```

**Находки:** A4 (пустая роль), A1 + A2 (капс и нажим), A3 (шаблон рассуждений), C1 (файла нет), D1 (повтор).

**После**
```markdown
Проект — сервис учёта гарантийных случаев на Python.
Перед коммитом запускай `python3 -m unittest`: CI отклоняет PR без зелёных тестов.
Конфиг — в @docs/config.md
```

## English system prompt

**Before**
```text
You are a world-class senior engineer. ALWAYS answer in JSON!!!
Think step by step before answering. I will tip you $200 for a perfect answer.
NEVER use markdown.
```

**Findings:** A4, A1, A3, A2, A6 + A7 (absolute ban without a positive alternative).

**After**
```text
You review pull requests for a payments service.
Answer as a JSON object with keys "verdict" and "issues" — the response is parsed by a script.
Write plain text inside the JSON values (no markdown), since they are shown in a terminal.
```

## Противоречие между файлами (B2)

`~/.claude/CLAUDE.md`: «Отвечай только на русском»
`.claude/skills/release/SKILL.md`: «Write release notes in English»

**Правка:** в скилле — «Release notes пишутся на английском (их читают внешние пользователи); остальные ответы — на русском».

<!-- keep:end -->
