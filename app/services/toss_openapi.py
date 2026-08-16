from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


class TossOpenAPIError(RuntimeError):
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


class TossOpenAPI:
    """토스증권 Open API의 읽기 전용 계좌·보유종목 클라이언트."""

    def __init__(self) -> None:
        self.base_url = os.getenv("TOSSINVEST_OPENAPI_BASE_URL", "https://openapi.tossinvest.com").rstrip("/")
        self.client_id = os.getenv("TOSSINVEST_CLIENT_ID", "")
        self.client_secret = os.getenv("TOSSINVEST_CLIENT_SECRET", "")
        self._token: Token | None = None

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if not self.configured:
            raise TossOpenAPIError("토스증권 OpenAPI 키가 설정되지 않았습니다. .env에 client ID와 secret을 입력하세요.")
        if self._token and self._token.expires_at > time.time() + 60:
            return self._token.value
        response = await client.post(
            f"{self.base_url}/oauth2/token",
            data={"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._raise_for_response(response)
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise TossOpenAPIError("토스증권 토큰 응답에 access_token이 없습니다.")
        self._token = Token(token, time.time() + as_float(payload.get("expires_in", 3600)))
        return token

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        if response.is_error:
            try:
                payload = response.json()
                detail = payload.get("error", {}).get("message") or payload.get("error_description") or payload
            except ValueError:
                detail = response.text
            raise TossOpenAPIError(f"토스증권 OpenAPI 요청 실패 ({response.status_code}): {detail}")

    async def _get(self, path: str, params: dict[str, Any] | None = None, account_seq: int | None = None) -> Any:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._access_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            if account_seq is not None:
                headers["X-Tossinvest-Account"] = str(account_seq)
            response = await client.get(f"{self.base_url}{path}", params=params, headers=headers)
            self._raise_for_response(response)
            payload = response.json()
        if "result" not in payload:
            raise TossOpenAPIError("토스증권 API 응답에 result가 없습니다.")
        return payload["result"]

    async def sync_holdings(self) -> list[dict[str, Any]]:
        accounts = await self._get("/api/v1/accounts")
        if isinstance(accounts, dict):
            accounts = accounts.get("items") or accounts.get("accounts") or []
        records: list[dict[str, Any]] = []
        for account in accounts:
            account_seq = account.get("accountSeq")
            if account_seq is None:
                continue
            overview = await self._get("/api/v1/holdings", account_seq=int(account_seq))
            if isinstance(overview, list):
                overview = {"items": overview}
            account_no = str(account.get("accountNo", ""))
            account_name = f"토스증권 계좌 {account_no[-4:]}" if account_no else f"토스증권 계좌 {account_seq}"
            for item in overview.get("items", []):
                country = item.get("marketCountry", "")
                records.append({
                    "account_key": str(account_seq),
                    "account_name": account_name,
                    "code": item.get("symbol", ""),
                    "name": item.get("name", ""),
                    "quantity": as_float(item.get("quantity")),
                    "avg_price": as_float(item.get("averagePurchasePrice")),
                    "current_price": as_float(item.get("lastPrice")),
                    "currency": item.get("currency", "KRW"),
                    "market": "KRX" if country == "KR" else "TOSS_US",
                })
        return [record for record in records if record["code"] and record["quantity"] > 0]

    async def get_exchange_rate(self, base_currency: str, quote_currency: str = "KRW") -> dict[str, Any]:
        """토스증권의 가장 최근 기준환율을 가져온다."""
        base_currency = base_currency.upper()
        quote_currency = quote_currency.upper()
        result = await self._get(
            "/api/v1/exchange-rate",
            params={"baseCurrency": base_currency, "quoteCurrency": quote_currency},
        )
        rate = as_float(result.get("rate"))
        if rate <= 0:
            raise TossOpenAPIError(f"토스증권 환율 응답에 유효한 {base_currency}/{quote_currency} 환율이 없습니다.")
        return {
            "rate": rate,
            "mid_rate": as_float(result.get("midRate")),
            "valid_from": result.get("validFrom"),
            "valid_until": result.get("validUntil"),
        }

    async def get_usd_krw_rate(self) -> dict[str, Any]:
        """기존 호출부와의 호환성을 위한 USD/KRW 편의 메서드."""
        return await self.get_exchange_rate("USD", "KRW")

    @staticmethod
    def _daily_change(candles: list[dict[str, Any]]) -> float | None:
        if len(candles) < 2:
            return None
        latest = as_float(candles[0].get("closePrice"))
        previous = as_float(candles[1].get("closePrice"))
        if previous <= 0:
            return None
        return (latest - previous) / previous * 100

    @staticmethod
    def _sparkline(candles: list[dict[str, Any]]) -> list[float]:
        return [as_float(item.get("closePrice")) for item in reversed(candles) if as_float(item.get("closePrice")) > 0]

    async def get_market_overview(self) -> list[dict[str, Any]]:
        """대시보드 상단에 표시할 주요 시장 지표를 토스증권에서 조회한다.

        토스증권의 시장지표 API는 코스피·코스닥만 직접 지원한다. 미국 두 지수는
        각각 이를 추종하는 대표 ETF(SPY·QQQ)의 가격으로 표시한다.
        """
        indicator_prices = await self._get("/api/v1/market-indicators/prices", params={"symbols": "KOSPI"})
        stock_prices = await self._get("/api/v1/prices", params={"symbols": "SPY,QQQ"})
        async def candle_pair(path: str, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            daily = await self._get(path, params={**params, "interval": "1d", "count": 2})
            try:
                intraday = await self._get(path, params={**params, "interval": "1m", "count": 120})
            except TossOpenAPIError:
                intraday = daily
            if len(intraday.get("candles", [])) < 3:
                intraday = daily
            return daily, intraday

        kospi_daily, kospi_intraday = await candle_pair("/api/v1/market-indicators/KOSPI/candles", {})
        spy_daily, spy_intraday = await candle_pair("/api/v1/candles", {"symbol": "SPY"})
        qqq_daily, qqq_intraday = await candle_pair("/api/v1/candles", {"symbol": "QQQ"})

        indicator_by_symbol = {str(item.get("symbol", "")).upper(): item for item in indicator_prices}
        price_by_symbol = {str(item.get("symbol", "")).upper(): item for item in stock_prices}
        market_rows = [
            ("KOSPI", "코스피", "국내 대표 지수", indicator_by_symbol.get("KOSPI", {}), kospi_daily, kospi_intraday),
            ("SPY", "S&P 500", "SPY 추종 ETF", price_by_symbol.get("SPY", {}), spy_daily, spy_intraday),
            ("QQQ", "나스닥100", "QQQ 추종 ETF", price_by_symbol.get("QQQ", {}), qqq_daily, qqq_intraday),
        ]
        overview: list[dict[str, Any]] = []
        for symbol, label, note, quote, daily_page, intraday_page in market_rows:
            overview.append({
                "symbol": symbol,
                "label": label,
                "note": note,
                "price": as_float(quote.get("lastPrice")),
                "currency": quote.get("currency", "KRW" if symbol == "KOSPI" else "USD"),
                "change_rate": self._daily_change(daily_page.get("candles", [])),
                "series": self._sparkline(intraday_page.get("candles", [])),
                "updated_at": quote.get("timestamp"),
            })
        return overview

    async def refresh_prices(self, holdings: list[dict[str, Any]]) -> tuple[dict[str, float], list[str]]:
        symbol_to_ids: dict[str, list[str]] = {}
        for holding in holdings:
            symbol = str(holding.get("code", "")).upper()
            if symbol:
                symbol_to_ids.setdefault(symbol, []).append(holding["id"])
        prices: dict[str, float] = {}
        warnings: list[str] = []
        symbols = list(symbol_to_ids)
        for start in range(0, len(symbols), 200):
            batch = symbols[start : start + 200]
            try:
                items = await self._get("/api/v1/prices", params={"symbols": ",".join(batch)})
            except TossOpenAPIError as exc:
                warnings.append(str(exc))
                continue
            found = set()
            for item in items:
                symbol = str(item.get("symbol", "")).upper()
                price = as_float(item.get("lastPrice"))
                if symbol and price > 0:
                    found.add(symbol)
                    for holding_id in symbol_to_ids.get(symbol, []):
                        prices[holding_id] = price
            for symbol in set(batch) - found:
                warnings.append(f"{symbol}: 토스증권 시세 응답이 없습니다.")
        return prices, warnings
