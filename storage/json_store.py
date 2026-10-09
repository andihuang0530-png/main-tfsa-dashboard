from __future__ import annotations

import json
from uuid import uuid4
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"


def data_path(name: str) -> Path:
    return DATA_DIR / name


def report_path(name: str) -> Path:
    return REPORTS_DIR / name


def read_json(name: str, default: Any) -> Any:
    path = data_path(name)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return default


def write_json(name: str, value: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = data_path(name)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    tmp_path.replace(path)


def write_report(name: str, content: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path(name).write_text(content, encoding="utf-8")


def load_settings() -> dict[str, Any]:
    return read_json("settings.json", {})


def save_settings(settings: dict[str, Any]) -> None:
    write_json("settings.json", settings)


def load_candidate_universe() -> list[dict[str, Any]]:
    return read_json("candidate_universe.json", [])


def save_candidate_universe(items: list[dict[str, Any]]) -> None:
    write_json("candidate_universe.json", items)


def load_watchlist() -> list[dict[str, Any]]:
    return read_json("watchlist.json", [])


def save_watchlist(items: list[dict[str, Any]]) -> None:
    write_json("watchlist.json", items)


def load_transactions() -> list[dict[str, Any]]:
    return read_json("transactions.json", [])


def save_transactions(items: list[dict[str, Any]]) -> None:
    write_json("transactions.json", items)
