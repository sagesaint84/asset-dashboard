from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


class NhPlugOpenAPIError(RuntimeError):
    pass


def as_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


class NhPlugOpenAPI:
    """NH투자증권(NHPLUG) 읽기 전용 잔고 조회 클라이언트."""

    _ALLOWED_HOSTS = {"api.nhplug.com", "moapi.nhplug.com"}
    _SUCCESS_CODES = {"00000", "00166", "00221", "13578"}
    _OVERSEAS_COUNTRIES = {
        "200": ("USD", "NH_US"),
        "070": ("JPY", "NH_JP"),
        "120": ("HKD", "NH_HK"),
        "160": ("CNY", "NH_CN"),
        "170": ("CNY", "NH_CN"),
    }

    def __init__(self) -> None:
        self.base_url = os.getenv("NHPLUG_BASE_URL", "https://api.nhplug.com:8443").rstrip("/")
        self.auth_url = os.getenv("NHPLUG_AUTH_URL", "https://api.nhplug.com:8443").rstrip("/")
        self.app_key = os.getenv("NHPLUG_APP_KEY", "")
        self.app_secret = os.getenv("NHPLUG_APP_SECRET", "")
        self._validate_url(self.base_url, "NHPLUG_BASE_URL")
        self._validate_url(self.auth_url, "NHPLUG_AUTH_URL")
        self.token_cache_file = Path(__file__).resolve().parents[2] / "data" / "nhplug_token_cache.json"
        self.last_accounts: list[dict[str, Any]] = []

    @staticmethod
    def _validate_url(value: str, setting: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname not in NhPlugOpenAPI._ALLOWED_HOSTS:
            raise NhPlugOpenAPIError(f"{setting}은 NHPLUG 공식 HTTPS 주소여야 합니다.")

    @property
    def configured(self) -> bool:
        return bool(self.app_key and self.app_secret)

    @property
    def is_mock(self) -> bool:
        return urlparse(self.base_url).hostname == "moapi.nhplug.com"

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if not self.configured:
            raise NhPlugOpenAPIError("나무증권 NHPLUG 앱 키가 설정되지 않았습니다. .env에 app key와 secret을 입력하세요.")
        try:
            cached = json.loads(self.token_cache_file.read_text(encoding="utf-8"))
            if (cached.get("app_key_prefix") == self.app_key[:8]
                    and float(cached.get("expires_at", 0)) > time.time() + 60
                    and cached.get("access_token")):
                return str(cached["access_token"])
        except (OSError, ValueError, TypeError):
            pass
        response = await client.post(
            f"{self.auth_url}/oauth2/token",
            params={
                "appkey": self.app_key,
                "appsecretkey": self.app_secret,
                "grant_type": "client_credentials",
                "scope": "oob",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._raise_for_response(response)
        token = response.json().get("access_token")
        if not token:
            raise NhPlugOpenAPIError("나무증권 토큰 응답에 access_token이 없습니다.")
        try:
            self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)
            expires_in = float(response.json().get("expires_in", 86400))
            self.token_cache_file.write_text(json.dumps({"app_key_prefix": self.app_key[:8], "access_token": token, "expires_at": time.time() + expires_in}, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
        return token

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        if response.is_error:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise NhPlugOpenAPIError(f"나무증권 OpenAPI 요청 실패 ({response.status_code}): {detail}")

    async def _call(self, path: str, input_0: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token = await self._access_token(client)
            response = await client.post(
                f"{self.base_url}{path}",
                headers={
                    "x-client-id": self.app_key,
                    "x-client-secret": self.app_secret,
                    "authorization": f"Bearer {token}",
                    "content-type": "application/json;charset=utf-8",
                },
                json={"Input_0": input_0},
            )
            self._raise_for_response(response)
            payload = response.json()
        code = str(payload.get("rsp_cd", ""))
        message = str(payload.get("rsp_msg", ""))
        if code not in self._SUCCESS_CODES and "완료" not in message:
            raise NhPlugOpenAPIError(f"나무증권 OpenAPI 응답 오류 ({code or '코드 없음'}): {message or payload}")
        return payload

    async def _accounts(self) -> list[dict[str, Any]]:
        payload = await self._call("/n2/acctinfo", {})
        accounts = payload.get("Output_0", [])
        if not isinstance(accounts, list):
            return []
        allowed_types = {"03"} if self.is_mock else {"01", "02"}
        return [account for account in accounts if str(account.get("acct_type", "")) in allowed_types]

    @staticmethod
    def _account_name(account: dict[str, Any]) -> str:
        account_no = str(account.get("acct_no", ""))
        return f"나무증권 계좌 {account_no[-4:]}" if account_no else "나무증권 계좌"

    async def sync_holdings(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        self.last_accounts = await self._accounts()
        for account in self.last_accounts:
            account_no = str(account.get("acct_no", ""))
            if not account_no:
                continue
            account_name = self._account_name(account)
            domestic = await self._call(
                "/krstock/inquiry/v1/balance",
                {"act_no": account_no, "bnc_bse_cd": "5", "ltg_aot_dit_cd": "9", "aet_bse": "2", "qut_dit_cd": "UNT"},
            )
            for item in domestic.get("Output_1", []) or []:
                records.append({
                    "account_key": account_no,
                    "account_name": account_name,
                    "code": item.get("iem_cd", ""),
                    "name": item.get("iem_nm", ""),
                    "quantity": as_float(item.get("itg_bnc_qty")),
                    "avg_price": as_float(item.get("phs_pr")),
                    "current_price": as_float(item.get("now_pr")),
                    "currency": "KRW",
                    "market": "KRX",
                })
            for country_code, (currency, market) in self._OVERSEAS_COUNTRIES.items():
                overseas = await self._call(
                    "/gbstock/inquiry/v1/balance",
                    {"act_no": account_no, "qut_iqr_dit_cd": "9", "fc_sec_trd_nat_cd": country_code, "cur_cd": "KRW", "xns_dit_cd": "1"},
                )
                for item in overseas.get("Output_1", []) or []:
                    records.append({
                        "account_key": account_no,
                        "account_name": account_name,
                        "code": item.get("iem_cd", ""),
                        "name": item.get("iem_nm") or item.get("oss_iem_eng_nm", ""),
                        "quantity": as_float(item.get("cns_bse_bnc_qty")),
                        "avg_price": as_float(item.get("fc_avg_phs_pr")),
                        "current_price": as_float(item.get("fc_sec_end_pr")),
                        "currency": item.get("cur_cd") or currency,
                        "market": market,
                    })
        return [record for record in records if record["code"] and record["quantity"] > 0]
