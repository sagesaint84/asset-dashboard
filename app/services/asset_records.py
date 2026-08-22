from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "data" / "asset_records.json"
_LOCK = threading.Lock()

EMPTY_RECORDS: dict[str, Any] = {"records": [], "updated_at": None}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(EMPTY_RECORDS, ensure_ascii=False, indent=2), encoding="utf-8")


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def read_asset_records() -> dict[str, Any]:
    with _LOCK:
        _ensure_data_file()
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = deepcopy(EMPTY_RECORDS)
        data.setdefault("records", [])
        data.setdefault("updated_at", None)
        normalized: list[dict[str, Any]] = []
        for item in data["records"]:
            if not isinstance(item, dict):
                continue
            normalized.append(normalize_record(item, preserve_id=True))
        normalized.sort(key=lambda item: (item.get("date") or "", item.get("created_at") or "", item.get("id") or ""))
        data["records"] = normalized
        return data


def write_asset_records(data: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        _ensure_data_file()
        data["updated_at"] = now_iso()
        temp_file = DATA_FILE.with_suffix(".json.tmp")
        temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(DATA_FILE)
        return data


def normalize_record(raw: dict[str, Any], preserve_id: bool = False) -> dict[str, Any]:
    record_id = str(raw.get("id") or uuid.uuid4()) if preserve_id else str(raw.get("id") or uuid.uuid4())
    date = str(raw.get("date") or "").strip()
    return {
        "id": record_id,
        "date": date,
        "owner": str(raw.get("owner") or "모두").strip(),  # 가족 구성원
        "total_value_krw": _coerce_float(raw.get("total_value_krw")),
        "total_cost_krw": _coerce_float(raw.get("total_cost_krw")),
        "profit_krw": _coerce_float(raw.get("profit_krw")),
        "return_rate": _coerce_float(raw.get("return_rate")),
        "day_profit_krw": _coerce_float(raw.get("day_profit_krw")),
        "krw_value_krw": _coerce_float(raw.get("krw_value_krw")),
        "usd_value_krw": _coerce_float(raw.get("usd_value_krw")),
        "holding_count": int(_coerce_float(raw.get("holding_count"))),
        "currency": str(raw.get("currency") or "KRW").upper(),
        "source": str(raw.get("source") or "manual"),
        "memo": str(raw.get("memo") or "").strip(),
        "created_at": str(raw.get("created_at") or now_iso()),
        "updated_at": str(raw.get("updated_at") or now_iso()),
    }


def list_asset_records() -> list[dict[str, Any]]:
    return read_asset_records()["records"]


def upsert_asset_record(raw: dict[str, Any], by_date: bool = False) -> dict[str, Any]:
    data = read_asset_records()
    record = normalize_record(raw)
    existing_index = None
    if by_date and record["date"]:
        # 날짜 + owner 복합 키로 매칭 (구성원별 독립 기록)
        owner = record.get("owner") or "모두"
        for index, item in enumerate(data["records"]):
            if item.get("date") == record["date"] and (item.get("owner") or "모두") == owner:
                existing_index = index
                record["id"] = item["id"]
                record["created_at"] = item.get("created_at") or record["created_at"]
                break
    elif record["id"]:
        for index, item in enumerate(data["records"]):
            if item.get("id") == record["id"]:
                existing_index = index
                record["created_at"] = item.get("created_at") or record["created_at"]
                break
    if existing_index is None:
        data["records"].append(record)
    else:
        data["records"][existing_index] = record
    write_asset_records(data)
    return record



def delete_asset_record(record_id: str) -> bool:
    data = read_asset_records()
    before = len(data["records"])
    data["records"] = [item for item in data["records"] if item.get("id") != record_id]
    if len(data["records"]) == before:
        return False
    write_asset_records(data)
    return True

