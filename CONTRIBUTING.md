# Contributing

Спасибо за интерес к проекту! / Thanks for your interest!

## Как помочь / How to help

1. **Ошибки и идеи** — откройте Issue (шаблоны в `.github/ISSUE_TEMPLATE/`).
2. **Изменения кода** — сделайте fork, отдельную ветку, PR с понятным описанием.
3. **Расчётное ядро** — `fan_selector/core.py` и `vfd.py` считают физику; любое
   изменение результата ломает golden-тесты (`tests/test_golden.py`). Golden-числа
   меняются только осознанно и с обоснованием в PR.
4. **Данные** — `data/*.json` — справочники; правки данных не требуют изменения кода,
   но проверяйте `python tests/test_golden.py`.

## Перед PR / Before a PR

```bash
cd fan-selector-plugin/core/select-radial-fan
python tests/test_golden.py
python tests/test_golden_fixture.py
```

CI (`ubuntu` + `windows`, Python 3.11/3.12) должен быть зелёным.

## Стиль / Style

- Python: 4 пробела, понятные имена, docstrings на русском (как в существующем коде).
- JS/TS: ESM, без лишних зависимостей.
- Коммиты: `feat:`, `fix:`, `docs:`, `ci:`, `refactor:`.
