from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from analysis.assets import default_currency, normalize_ticker


MOCK_OVERRIDES: dict[str, dict[str, Any]] = {
    "NVDA": {
        "latestClose": 198.0,
        "marketCap": "4.9T",
        "sector": "Technology",
        "return1w": 2.7,
        "return1m": 8.4,
        "return3m": 18.1,
        "return6m": 32.0,
        "return1y": 71.0,
        "week52High": 205.0,
        "week52Low": 86.0,
        "ma50": 184.0,
        "ma200": 141.0,
        "rsi": 73,
        "volatility": 34,
        "beta": 1.75,
        "peRatio": 45,
        "forwardPe": 31,
        "revenueGrowth": 42,
        "epsGrowth": 51,
        "profitMargin": 54,
        "earningsDate": "2026-05-27",
        "dividendYield": 0.03,
        "newsSummary": "AI accelerator demand remains strong; valuation and concentration risk are elevated.",
    },
    "VFV.TO": {
        "latestClose": 174.0,
        "return1m": 3.2,
        "return3m": 6.5,
        "return6m": 11.2,
        "return1y": 18.4,
        "week52High": 176.0,
        "week52Low": 136.0,
        "ma50": 169.0,
        "ma200": 158.0,
        "rsi": 61,
        "volatility": 13,
        "expenseRatio": 0.09,
        "aum": "18.5B",
        "dividendYield": 1.2,
        "topHoldings": ["AAPL", "MSFT", "NVDA", "AMZN", "META"],
        "sectorExposure": ["Technology", "Financials", "Health Care", "Consumer Discretionary"],
        "newsSummary": "Broad U.S. equity exposure remains a core long-term ETF sleeve.",
    },
    "TEC.TO": {
        "latestClose": 47.5,
        "return1m": 5.1,
        "return3m": 10.3,
        "return6m": 18.5,
        "return1y": 29.0,
        "week52High": 49.0,
        "week52Low": 34.0,
        "ma50": 45.0,
        "ma200": 40.5,
        "rsi": 66,
        "volatility": 21,
        "expenseRatio": 0.39,
        "aum": "6.2B",
        "dividendYield": 0.4,
        "topHoldings": ["MSFT", "AAPL", "NVDA", "AVGO", "GOOGL"],
        "sectorExposure": ["Technology", "Communication Services", "Consumer Discretionary"],
        "newsSummary": "Global technology exposure is benefiting from AI and cloud demand.",
    },
    "MSFT": {
        "latestClose": 468.0,
        "marketCap": "3.5T",
        "sector": "Technology",
        "return1w": 1.1,
        "return1m": 4.2,
        "return3m": 8.1,
        "return6m": 17.0,
        "return1y": 24.0,
        "week52High": 482.0,
        "week52Low": 365.0,
        "ma50": 456.0,
        "ma200": 421.0,
        "rsi": 58,
        "volatility": 19,
        "beta": 0.95,
        "peRatio": 36,
        "forwardPe": 29,
        "revenueGrowth": 16,
        "epsGrowth": 18,
        "profitMargin": 36,
        "earningsDate": "2026-07-28",
        "dividendYield": 0.7,
        "newsSummary": "Cloud and AI platform momentum remain supportive.",
    },
    "XQQ.TO": {
        "latestClose": 139.0,
        "return1m": 4.3,
        "return3m": 9.6,
        "return6m": 16.1,
        "return1y": 26.0,
        "week52High": 142.0,
        "week52Low": 108.0,
        "ma50": 136.0,
        "ma200": 126.0,
        "rsi": 64,
        "volatility": 18,
        "expenseRatio": 0.39,
        "aum": "3.7B",
        "dividendYield": 0.6,
        "topHoldings": ["MSFT", "AAPL", "NVDA", "AMZN", "AVGO"],
        "sectorExposure": ["Technology", "Communication Services", "Consumer Discretionary"],
        "newsSummary": "CAD-hedged NASDAQ 100 exposure remains growth oriented.",
    },
}


class MockMarketProvider:
    name = "mock"

    def get_quotes(self, candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {normalize_ticker(item["ticker"]): self.get_quote(item["ticker"], item) for item in candidates}

    def get_quote(self, ticker: str, metadata: dict[str, Any]) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        seed = sum(ord(char) for char in ticker)
        asset_type = metadata.get("type", "US Stock")
        is_etf = asset_type.endswith("ETF")
        currency = default_currency(ticker, asset_type)
        base_price = 25 + (seed % 190)
        if currency == "USD" and not is_etf:
            base_price += 85
        volatility = 10 + (seed % 30)
        rsi = 42 + (seed % 36)
        return_1m = round(((seed % 17) - 4) * 0.9, 1)
        return_3m = round(return_1m + 2 + (seed % 10), 1)
        return_6m = round(return_3m + 4 + (seed % 12), 1)
        return_1y = round(return_6m + 5 + (seed % 25), 1)
        high = round(base_price * (1.05 + (seed % 8) / 100), 2)
        low = round(base_price * (0.62 + (seed % 12) / 100), 2)
        latest = round(base_price * (0.9 + (seed % 16) / 100), 2)
        ma50 = round(latest * (0.95 + (seed % 8) / 100), 2)
        ma200 = round(latest * (0.86 + (seed % 14) / 100), 2)
        next_earnings = date.today() + timedelta(days=14 + (seed % 60))

        quote = {
            "ticker": ticker,
            "name": metadata.get("name", ticker),
            "type": asset_type,
            "theme": metadata.get("theme", "N/A"),
            "riskLevel": metadata.get("riskLevel", "Medium"),
            "isCore": bool(metadata.get("isCore", False)),
            "dataStatus": "ok",
            "latestClose": latest,
            "currency": currency,
            "marketCap": f"{round((seed % 900 + 50) / 10, 1)}B",
            "sector": "Technology" if not is_etf else "N/A",
            "return1w": round(((seed % 9) - 2) * 0.7, 1),
            "return1m": return_1m,
            "return3m": return_3m,
            "return6m": return_6m,
            "return1y": return_1y,
            "week52High": high,
            "week52Low": low,
            "distanceFrom52WeekHigh": round((latest / high - 1) * 100, 1),
            "distanceFrom52WeekLow": round((latest / low - 1) * 100, 1),
            "ma50": ma50,
            "ma200": ma200,
            "rsi": rsi,
            "volatility": volatility,
            "beta": round(0.75 + (seed % 75) / 50, 2),
            "peRatio": None if is_etf else round(18 + (seed % 40), 1),
            "forwardPe": None if is_etf else round(16 + (seed % 32), 1),
            "revenueGrowth": None if is_etf else round(5 + (seed % 35), 1),
            "epsGrowth": None if is_etf else round(4 + (seed % 45), 1),
            "profitMargin": None if is_etf else round(12 + (seed % 35), 1),
            "earningsDate": None if is_etf else next_earnings.isoformat(),
            "dividendYield": round((seed % 28) / 10, 2),
            "expenseRatio": round(0.04 + (seed % 55) / 100, 2) if is_etf else None,
            "aum": f"{round((seed % 700 + 20) / 10, 1)}B" if is_etf else None,
            "topHoldings": ["MSFT", "AAPL", "NVDA", "AMZN", "GOOGL"] if is_etf else None,
            "sectorExposure": ["Technology", "Communication Services", "Consumer Discretionary"] if is_etf else None,
            "newsSummary": "Mock research summary. News provider is not configured for the MVP.",
        }
        quote.update(MOCK_OVERRIDES.get(ticker, {}))
        quote["distanceFrom52WeekHigh"] = round((quote["latestClose"] / quote["week52High"] - 1) * 100, 1)
        quote["distanceFrom52WeekLow"] = round((quote["latestClose"] / quote["week52Low"] - 1) * 100, 1)
        return quote
