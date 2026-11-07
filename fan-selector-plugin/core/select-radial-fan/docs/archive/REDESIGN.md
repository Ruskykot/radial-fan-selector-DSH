> Исторический документ: описывает раннюю архитектуру, к текущему коду отношения не имеет. Оставлен для истории.

# Переработка проекта: интеграция с DeepSeek Harness как skill

## Статус: ВЫПОЛНЕНО (историческая заметка; актуальное состояние — корневой [README](../../../../README.md))

Проект переработан в расчётное ядро + DSH-навык. Все лишние интерфейсы удалены,
качество расчётов сохранено (golden-тесты зелёные).

## Итоговая структура (21 файл)

```
select-radial-fan/
├── data/                  # fans.json, impellers.json, motors.json, config.json
├── fan_selector/
│   ├── __init__.py        # экспорт run_selection
│   ├── models.py          # доменные модели (не тронуты)
│   ├── config.py          # конфигурация/валидация (не тронута)
│   ├── repositories.py    # загрузка данных (resource_path заменён на env-путь)
│   ├── core.py            # расчётное ядро (НЕ тронуто)
│   ├── selector.py        # оркестратор (не тронут)
│   ├── select.py          # универсальный адаптер run_selection(dict)->dict
│   └── __main__.py        # python -m fan_selector --json
├── schema/                # selection.schema.json, result.schema.json
├── .dsh/skills/fan-selector/SKILL.md   # навык DSH с ветвящимся деревом вопросов
├── tests/test_golden.py   # golden-тесты
├── README.md, REDESIGN.md, requirements.txt, pyproject.toml, .gitignore
```

## Удалено

- `pdf_report.py` (PDF + reportlab), `web/` (FastAPI + 7 HTML + slowapi + matplotlib)
- `history.py` + `history.db` (SQLite), `cli.py`/`cli_enter.py`/`main.py` (CLI-дубль)
- `resource_path.py` (PyInstaller), `FanSelector.spec` + `BUILD.md` + `scripts/` + `.github/`
- `build/`, `dist/`, `docs/`, `PR_DESCRIPTION.md`, `reports/`, `fan_selector.egg-info/`
- `.kilo/`, `.vscode/`, `.idea/`, `github-mcp/`, тестовые PNG, корневые Office-файлы
- зависимости: reportlab, matplotlib, fastapi, uvicorn, slowapi, python-multipart, httpx, tzdata

Осталось только `numpy`.

## Навык DSH

- Авто-обнаружение через `.dsh/skills/fan-selector/SKILL.md`.
- Агент ведёт ветвящийся диалог через `ask_user_question`:
  расход/давление → тип давления → серия (ВР 86-77 / ВР 280-46) → типоразмер
  (2.5/4/6.3) → обороты (1000/1500/3000) → мощность двигателя.
- Уточнения выводятся запросами агенту, а не текстом.
- График/таблицу строит сам харнесс по данным `curve` в результате.

## Гарантия качества

Эталон (Q=7500, P=700, FULL): 10 вариантов в выдаче, 9 прошли.
- ВР 280-46-6.3(1DN)-Y-X/750: ΔP=47.56, η=0.6292, N=2846.61 Вт, дв. 160S8 (7.5 кВт, 750 об/мин)
- ВР 86-77-8(0.9DN)-Y-X/1000: ΔP=125.09, дв. 112MB6 (4.0 кВт, 1000 об/мин)

`tests/test_golden.py` — все 8 тестов зелёные.

