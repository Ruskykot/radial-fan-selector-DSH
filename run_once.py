"""Одноразовый расчётный раннер fan_selector: JSON на stdin -> JSON на stdout.

Используется плагином DSH для подбора без постоянно висящего HTTP-сервера.

Вход:  {"op": "...", "payload": {...}}
  op: select | chart | compare | catalog | parse_csv | batch
Выход: результат соответствующей функции fan_selector.select (JSON).
"""
import base64
import csv
import io
import json
import os
import sys
from pathlib import Path

# На Windows при передаче через пайп stdin/stdout используют ANSI-кодировку
# локали (например cp1251), из-за чего кириллица в названиях вентиляторов
# при чтении в Node превращается в "?". Принудительно переключаем на UTF-8,
# чтобы и входные данные (система/комментарий), и результат шли в UTF-8.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass

# Ядро fan_selector ищется по порядку:
#   1) FAN_SELECTOR_CORE — явный путь к пакету;
#   2) select-radial-fan/ рядом с этим файлом (монорепозиторий);
#   3) уже установленный pip-пакет fan_selector (site-packages) — без правок пути.
_core = os.environ.get("FAN_SELECTOR_CORE")
if _core and Path(_core).is_dir():
    sys.path.insert(0, _core)
elif (Path(__file__).resolve().parent / "select-radial-fan").is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parent / "select-radial-fan"))

from fan_selector.select import (  # noqa: E402
    run_selection,
    chart_selection,
    run_comparison,
    catalog_lookup,
)

_MAX_BATCH_ROWS = 5000

_OPERATIONS = {
    "select": run_selection,
    "chart": chart_selection,
    "compare": run_comparison,
    "catalog": catalog_lookup,
}


# ---------------------------------------------------------------------------
# CSV-разбор (массовый подбор)
# ---------------------------------------------------------------------------

def _decode_csv_text(csv_b64):
    raw = base64.b64decode(csv_b64 or "")
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _map_header(raw):
    h = str(raw or "").lstrip("\ufeff").strip().lower()
    h = " ".join(h.split())
    if not h:
        return None
    exact = {
        "q": "q_req", "q_req": "q_req", "qreq": "q_req",
        "p": "p_req", "p_req": "p_req", "preq": "p_req",
        "pressure_type": "pressure_type", "pressuretype": "pressure_type",
        "regulation_mode": "regulation_mode", "regulationmode": "regulation_mode",
        "mode": "regulation_mode",
        "d_reg_max": "d_reg_max", "dregmax": "d_reg_max",
        "t_air": "t_air", "tair": "t_air",
        "freq_min_hz": "freq_min_hz", "freq_max_hz": "freq_max_hz",
        "fmin": "freq_min_hz", "fmax": "freq_max_hz",
        "system": "system", "comment": "comment",
    }
    if h in exact:
        return exact[h]
    if "систем" in h:
        return "system"
    if "коммент" in h or "примечани" in h:
        return "comment"
    if "расход" in h or "производительност" in h:
        return "q_req"
    if "тип давлен" in h:
        return "pressure_type"
    if "дорегул" in h:
        return "d_reg_max"
    if "температур" in h:
        return "t_air"
    if "мин" in h and ("частот" in h or "гц" in h or h.startswith("f")):
        return "freq_min_hz"
    if "макс" in h and ("частот" in h or "гц" in h or h.startswith("f")):
        return "freq_max_hz"
    if "режим" in h or "регулирован" in h:
        return "regulation_mode"
    if "давлен" in h:
        return "p_req"
    return None


def _norm_num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    s = s.replace(",", ".").replace(" ", "").replace("\xa0", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_pressure(v):
    s = str(v or "").strip().lower()
    if s in ("static", "статическое", "статич", "статический"):
        return "STATIC"
    return "FULL"


def _parse_mode(v):
    s = str(v or "").strip().lower()
    if s in ("vfd", "чрп", "частотное", "частотный", "frequency", "частотное регулирование"):
        return "VFD"
    if s in ("compare", "сравнение", "сравнения", "сравн"):
        return "COMPARE"
    return "THROTTLE"


def _parse_csv_rows(text):
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delim = ";" if ";" in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    return [r for r in reader]


def _row_to_point(header, mapping, row):
    raw = {}
    for key, val in zip(mapping, row):
        if key:
            raw[key] = (val or "").strip()
    q = _norm_num(raw.get("q_req"))
    p = _norm_num(raw.get("p_req"))
    if q is None or q <= 0 or p is None or p <= 0:
        raise ValueError("задайте положительные Q и P")
    point = {
        "q_req": q,
        "p_req": p,
        "pressure_type": _parse_pressure(raw.get("pressure_type")),
        "regulation_mode": _parse_mode(raw.get("regulation_mode")),
        "system": raw.get("system", ""),
        "comment": raw.get("comment", ""),
    }
    for key, field in (
        ("d_reg_max", "d_reg_max"),
        ("t_air", "t_air"),
        ("freq_min_hz", "freq_min_hz"),
        ("freq_max_hz", "freq_max_hz"),
    ):
        val = _norm_num(raw.get(key))
        if val is not None:
            point[field] = val
    if point.get("regulation_mode") == "COMPARE":
        raise ValueError("Сравнение доступно только в единичном подборе")
    return point


def _parse_table(payload):
    text = _decode_csv_text(payload.get("csvBase64"))
    rows = _parse_csv_rows(text)
    if not rows:
        raise ValueError("Файл пуст")
    header = rows[0]
    mapping = [_map_header(h) for h in header]
    if "q_req" not in mapping or "p_req" not in mapping:
        raise ValueError("Не найдены обязательные колонки 'Расход Q' и 'Давление P'")
    data_rows = [r for r in rows[1:] if any((c or "").strip() for c in r)]
    return header, mapping, data_rows


def parse_csv(payload):
    try:
        header, mapping, data_rows = _parse_table(payload)
    except ValueError as e:
        return {"schema": "fan-batch-preview/v1",
                "error": {"code": "INVALID_INPUT", "message": str(e)}}
    errors = []
    valid = 0
    for i, row in enumerate(data_rows, start=1):
        try:
            _row_to_point(header, mapping, row)
            valid += 1
        except ValueError as e:
            errors.append({"row": i, "message": str(e)})
    first_rows = []
    for i, row in enumerate(data_rows[:3], start=1):
        d = {}
        for key, val in zip(mapping, row):
            if key:
                d[key] = (val or "").strip()
        first_rows.append({"row": i, **d})
    return {
        "schema": "fan-batch-preview/v1",
        "fileName": payload.get("fileName", ""),
        "totalRows": len(data_rows),
        "validRows": valid,
        "columns": [str(h).strip() for h in header],
        "firstRows": first_rows,
        "errors": errors[:20],
    }


_SLIM_KEYS = ("model", "series", "size", "dn", "d_over_dn", "max_n", "q_work", "p_work",
              "d_reg_pa", "eta_req", "f_hz", "n_rpm", "n_in_w", "motor", "vfd",
              "noise_body_dba", "mass")


def _slim_result(r):
    return {k: r.get(k) for k in _SLIM_KEYS if k in r}


def _compact_row(index, point, res):
    q = res.get("query", {})
    results = res.get("results", [])
    passed = [r for r in results if r.get("passed")]
    best = _slim_result(passed[0]) if passed else None
    return {
        "index": index,
        "ok": True,
        "q_req": q.get("q_req"),
        "p_req": q.get("p_req"),
        "pressure_type": q.get("pressure_type", "FULL"),
        "regulation_mode": q.get("regulation_mode", "THROTTLE"),
        "d_reg_max": q.get("d_reg_max", 1500.0),
        "t_air": q.get("t_air", 20.0),
        "freq_min_hz": q.get("freq_min_hz", 20.0),
        "freq_max_hz": q.get("freq_max_hz", 60.0),
        "system": point.get("system", ""),
        "comment": point.get("comment", ""),
        "total": res.get("summary", {}).get("total", 0),
        "passed": res.get("summary", {}).get("passed", 0),
        "best": best,
    }


def run_batch(payload):
    try:
        header, mapping, data_rows = _parse_table(payload)
        if len(data_rows) > _MAX_BATCH_ROWS:
            raise ValueError("Слишком много строк (максимум %d)" % _MAX_BATCH_ROWS)
    except ValueError as e:
        return {"schema": "fan-batch/v1",
                "error": {"code": "INVALID_INPUT", "message": str(e)}}

    out_rows = []
    for i, row in enumerate(data_rows, start=1):
        try:
            point = _row_to_point(header, mapping, row)
        except ValueError as e:
            out_rows.append({"index": i, "ok": False,
                             "error": {"code": "INVALID_INPUT", "message": str(e), "row": i}})
            continue
        try:
            res = run_selection(point)
        except Exception as e:  # noqa: BLE001
            out_rows.append({"index": i, "ok": False,
                             "error": {"code": "CALC_ERROR", "message": str(e), "row": i}})
            continue
        if "error" in res:
            out_rows.append({"index": i, "ok": False, "system": point.get("system", ""),
                             "error": {"code": res["error"].get("code", "CALC_ERROR"),
                                       "message": res["error"].get("message", "ошибка"), "row": i}})
            continue
        out_rows.append(_compact_row(i, point, res))

    passed = sum(1 for r in out_rows if r.get("ok") and r.get("best"))
    return {
        "schema": "fan-batch/v1",
        "fileName": payload.get("fileName", ""),
        "count": len(data_rows),
        "passed": passed,
        "rows": out_rows,
    }


_OPERATIONS["parse_csv"] = parse_csv
_OPERATIONS["batch"] = run_batch


def main() -> None:
    raw = sys.stdin.read()
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError:
        req = {}
    op = req.get("op", "select")
    payload = req.get("payload", {})
    fn = _OPERATIONS.get(op, run_selection)
    try:
        result = fn(payload)
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema": "fan-result/v1",
            "error": {"code": "CALC_ERROR", "message": str(exc)},
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
