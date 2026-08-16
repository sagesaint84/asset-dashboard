from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


class KBOpenAPIError(RuntimeError):
    pass


def as_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Token:
    value: str
    expires_at: float


class KBOpenAPI:
    """KB B2C OpenAPI client. Credentials live only in the server environment."""

    def __init__(self) -> None:
        self.base_url = os.getenv("KB_OPENAPI_BASE_URL", "https://developer.kbsec.com:32484").rstrip("/")
        self.app_key = os.getenv("KB_OPENAPI_APP_KEY", "")
        self.app_secret = os.getenv("KB_OPENAPI_APP_SECRET", "")
        self._token: Token | None = None

    @property
    def configured(self) -> bool:
        return bool(self.app_key and self.app_secret)

    @staticmethod
    def _payload(data_body: dict[str, Any]) -> dict[str, Any]:
        return {"dataHeader": {"ipAddr": "", "macAddr": ""}, "dataBody": data_body}

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if not self.configured:
            raise KBOpenAPIError("KB OpenAPI 키가 설정되지 않았습니다. .env에 appKey와 appSecret을 입력하세요.")
        if self._token and self._token.expires_at > time.time() + 60:
            return self._token.value
        response = await client.post(
            f"{self.base_url}/oauth2/token",
            json=self._payload({"appKey": self.app_key, "appSecret": self.app_secret, "grantType": "client_credentials"}),
        )
        self._raise_for_response(response)
        body = response.json().get("dataBody", response.json())
        token = body.get("access_token")
        if not token:
            raise KBOpenAPIError("KB OpenAPI 토큰 응답에 access_token이 없습니다.")
        self._token = Token(token, time.time() + as_float(body.get("expires_in", 3600)))
        return token

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        if response.is_error:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise KBOpenAPIError(f"KB OpenAPI 요청 실패 ({response.status_code}): {detail}")

    async def call(self, endpoint: str, data_body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._access_token(client)
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers={"Content-Type": "application/json", "appKey": self.app_key, "Authorization": f"bearer {token}"},
                json=self._payload(data_body),
            )
            self._raise_for_response(response)
            payload = response.json()
        body = payload.get("dataBody", payload)
        code = str(body.get("o_clsf", body.get("clsfP", "0")))
        if code not in {"", "0", "00"}:
            raise KBOpenAPIError(body.get("o_msg", body.get("msg", "KB OpenAPI가 오류를 반환했습니다.")))
        return body

    async def sync_holdings(self) -> list[dict[str, Any]]:
        domestic, overseas = await asyncio.gather(
            self.call("/api/v1/ssqm1801", {"inq_clsf": "0", "mkt_tm_ccd": "1", "is_no": "", "nxt_key": ""}),
            self.call("/api/v1/spqm2226", {"std_crncy_f": "2", "exch_r_aplc_f": "2", "fee_clsf": "0", "cn_f": "0", "nxt_key": "", "mktpr_aplc_clsf": ""}),
        )
        records: list[dict[str, Any]] = []
        for row in domestic.get("Record1", []):
            code = str(row.get("is_no", ""))[-6:]
            records.append({"code": code, "name": row.get("is_nm", code), "quantity": as_float(row.get("gnrl_q")), "avg_price": 0, "current_price": 0, "currency": "KRW", "market": "KRX"})
        for row in overseas.get("Record2", []):
            records.append({"code": row.get("is_cd", ""), "name": row.get("is_nm", ""), "quantity": as_float(row.get("frgn_hld_q_p6")), "avg_price": as_float(row.get("byng_avr_prc_p4")), "current_price": as_float(row.get("now_prc_p4")), "currency": row.get("crncy_clsf_nm", "USD"), "market": row.get("mkt_clsf", "")})
        return [row for row in records if row["code"] and row["quantity"] > 0]

    async def refresh_prices(self, holdings: list[dict[str, Any]]) -> tuple[dict[str, float], list[str]]:
        prices: dict[str, float] = {}
        errors: list[str] = []

        async def refresh(holding: dict[str, Any]) -> None:
            key = holding["id"]
            try:
                if holding.get("market") == "KRX" and str(holding.get("code", "")).isdigit():
                    body = await self.call("/api/v1/ivu10140", {"excg_clsf": "0", "shrt_cd": str(holding["code"])[-6:]})
                    price = as_float(body.get("now_prc"))
                elif holding.get("market"):
                    body = await self.call("/api/v1/gss10030", {"krx_cd": holding["market"], "is_cd": holding["code"]})
                    price = as_float(body.get("now_prc_p4"))
                else:
                    errors.append(f"{holding['name']}: 거래소 코드가 없어 시세를 조회하지 못했습니다.")
                    return
                if price > 0:
                    prices[key] = price
                else:
                    errors.append(f"{holding['name']}: 유효한 현재가가 응답되지 않았습니다.")
            except KBOpenAPIError as exc:
                errors.append(f"{holding['name']}: {exc}")

        await asyncio.gather(*(refresh(holding) for holding in holdings))
        return prices, errors
