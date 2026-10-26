---
name: clean-skill
description: >
  Собирает краткую сводку по CSV-выгрузке. Use when asked to summarize a CSV export
  or «сделай сводку по выгрузке».
---

# clean-skill

Шаг 1. Запусти `scripts/run.py` с путём к выгрузке.

```bash
python3 scripts/run.py data.csv
```

Шаг 2. Покажи сводку таблицей. Ключ берётся из `os.environ["API_TOKEN"]`, в конфиге стоит `token = "<your-token>"`.

Вопросы по скиллу: support@example.com. Версия 1.1.0 от 2026-10-26.
