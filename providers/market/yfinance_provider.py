from __future__ import annotations

from typing import Any


class YFinanceProvider:
    name = "yfinance"

    def __init__(self) -> None:
        try:
            import yfinance as yf  # type: ignore
        except Exception:
            yf = None
        self.yf = yf

    def available(self) -> bool:
        return self.yf is not None

    def get_quotes(self, candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if not self.available():
            return {}
        return {item["ticker"]: self.get_quote(item["ticker"], item) for item in candidates}

    def get_quote(self, ticker: str, metadata: dict[str, Any]) -> dict[str, Any]:
        if not self.available():
            return {"ticker": ticker, "dataStatus": "unavailable"}
        try:
            ticker_obj = self.yf.Ticker(ticker)
            hist = ticker_obj.history(period="1y")
            if hist.empty:
                return {"ticker": ticker, "dataStatus": "unavailable"}
            latest = float(hist["Close"].iloc[-1])
            return {
                "ticker": ticker,
                "name": metadata.get("name", ticker),
                "type": metadata.get("type"),
                "theme": metadata.get("theme"),
                "riskLevel": metadata.get("riskLevel"),
                "dataStatus": "ok",
                "latestClose": round(latest, 2),
                "currency": "CAD" if ticker.endswith(".TO") else "USD",
            }
        except Exception:
            return {"ticker": ticker, "dataStatus": "unavailable"}
