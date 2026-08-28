from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
USERS_DIR = DATA_DIR / "users"


def _get_user_openapi_file(username: str) -> Path:
    user_dir = USERS_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "openapi_config.json"


def get_user_openapi_config(username: str) -> dict[str, dict[str, str]]:
    """사용자의 OpenAPI 설정을 조회합니다.
    
    sagesaint 계정의 경우 개별 파일이 없으면 기존 .env 값을 fallback으로 지원합니다.
    """
    file_path = _get_user_openapi_file(username)
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("사용자 %s의 openapi_config.json 파싱 실패: %s", username, e)

    # fallback: sagesaint 계정일 때만 .env 기본값을 읽어와 부트스트랩
    if username == "sagesaint":
        env_config = {
            "toss": {
                "app_key": os.getenv("TOSSINVEST_CLIENT_ID", "").strip(),
                "app_secret": os.getenv("TOSSINVEST_CLIENT_SECRET", "").strip(),
            },
            "kb": {
                "app_key": os.getenv("KB_OPENAPI_APP_KEY", "").strip(),
                "app_secret": os.getenv("KB_OPENAPI_APP_SECRET", "").strip(),
            },
            "nh": {
                "app_key": os.getenv("NHPLUG_APP_KEY", "").strip(),
                "app_secret": os.getenv("NHPLUG_APP_SECRET", "").strip(),
            },
        }
        return env_config

    return {
        "toss": {"app_key": "", "app_secret": ""},
        "kb": {"app_key": "", "app_secret": ""},
        "nh": {"app_key": "", "app_secret": ""},
    }


def save_user_openapi_config(username: str, update_data: dict[str, dict[str, str]]) -> dict[str, Any]:
    """사용자의 OpenAPI 설정을 저장합니다. 마스킹된 값(****)은 기존 값을 보존합니다."""
    current = get_user_openapi_config(username)

    for broker in ("toss", "kb", "nh"):
        if broker in update_data:
            b_data = update_data[broker]
            current.setdefault(broker, {})
            
            # app_key
            new_key = b_data.get("app_key", "").strip()
            if new_key and not new_key.endswith("****"):
                current[broker]["app_key"] = new_key
            elif new_key == "":
                current[broker]["app_key"] = ""

            # app_secret
            new_sec = b_data.get("app_secret", "").strip()
            if new_sec and not new_sec.startswith("****") and new_sec != "********":
                current[broker]["app_secret"] = new_sec
            elif new_sec == "":
                current[broker]["app_secret"] = ""

    file_path = _get_user_openapi_file(username)
    file_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("사용자 %s의 OpenAPI 설정 저장 완료", username)
    return current


def get_masked_user_openapi_config(username: str) -> dict[str, dict[str, Any]]:
    """UI 표시용 마스킹된 OpenAPI 설정 반환"""
    cfg = get_user_openapi_config(username)
    masked: dict[str, dict[str, Any]] = {}

    for broker in ("toss", "kb", "nh"):
        b_cfg = cfg.get(broker, {})
        key = b_cfg.get("app_key", "")
        sec = b_cfg.get("app_secret", "")

        masked_key = ""
        if key:
            prefix = key[:4] if len(key) >= 4 else key
            masked_key = f"{prefix}****"

        masked_sec = "********" if sec else ""

        masked[broker] = {
            "app_key": masked_key,
            "has_app_key": bool(key),
            "app_secret": masked_sec,
            "has_app_secret": bool(sec),
            "configured": bool(key and sec),
        }

    return masked
