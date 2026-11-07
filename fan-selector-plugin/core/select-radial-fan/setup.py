"""Build hook: поставлять справочники ``data/*.json`` вместе с пакетом.

Каноническое расположение справочников — ``select-radial-fan/data/`` рядом с
пакетом ``fan_selector/`` (так их видят запуск из репозитория и editable-установка,
см. ``fan_selector/repositories.py``). В wheel нельзя ссылаться на пути вне пакета,
поэтому на этапе сборки JSON-файлы копируются в ``fan_selector/data/`` внутри
``build_lib`` и попадают в установленный пакет.

Запускается автоматически: ``pip install ./select-radial-fan``, ``pip wheel .``,
``python -m build``. Для sdist файлы включает ``MANIFEST.in``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class build_py_with_data(build_py):
    """Скопировать ``data/*.json`` в ``fan_selector/data/`` в каталоге сборки."""

    def run(self) -> None:
        super().run()

        root = Path(__file__).resolve().parent
        source = root / "data"
        if not source.is_dir():
            # sdist мог быть собран без data/ — не роняем сборку, укажем проблему.
            print(f"warning: reference data directory not found: {source}")
            return

        target = Path(self.build_lib) / "fan_selector" / "data"
        target.mkdir(parents=True, exist_ok=True)

        copied = 0
        for item in sorted(source.glob("*.json")):
            shutil.copy2(item, target / item.name)
            copied += 1
        print(f"fan-selector: copied {copied} reference JSON files into fan_selector/data")


setup(cmdclass={"build_py": build_py_with_data})
