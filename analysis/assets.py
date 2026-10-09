from __future__ import annotations

from datetime import datetime
from typing import Any


SUPPORTED_US_STOCKS = {
    "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "MU", "QCOM", "AVGO",
    "AMD", "ORCL", "CRM", "TSM", "ASML", "LRCX", "AMAT", "KLAC", "VRT",
    "ETN", "CEG", "NEE", "ADBE", "NOW", "SNOW", "PANW", "CRWD"
}
SUPPORTED_US_ETFS = {"QQQ", "SMH", "SOXX", "AIQ", "BOTZ", "VOO", "VTI"}
SUPPORTED_CAD_ETFS = {
    "VFV.TO", "XQQ.TO", "ZQQ.TO", "TEC.TO", "XCHP.TO", "CHPS.TO",
    "XEQT.TO", "VEQT.TO", "XGRO.TO"
}


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def infer_asset_type(ticker: str) -> str | None:
    ticker = normalize_ticker(ticker)
    if ticker in SUPPORTED_CAD_ETFS:
        return "CAD ETF"
    if ticker in SUPPORTED_US_ETFS:
        return "US ETF"
    if ticker in SUPPORTED_US_STOCKS:
        return "US Stock"
    return None


def is_supported_ticker(ticker: str) -> bool:
    return infer_asset_type(ticker) is not None


def default_currency(ticker: str, asset_type: str | None = None) -> str:
    asset_type = asset_type or infer_asset_type(ticker)
    return "CAD" if asset_type == "CAD ETF" else "USD"


def candidate_lookup(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {normalize_ticker(item["ticker"]): item for item in candidates}


def build_candidate_for_ticker(ticker: str) -> dict[str, Any] | None:
    ticker = normalize_ticker(ticker)
    asset_type = infer_asset_type(ticker)
    if not asset_type:
        return None
    theme = "broad market ETF" if asset_type.endswith("ETF") else "defensive growth"
    risk = "Low" if theme == "broad market ETF" else "Medium"
    return {
        "ticker": ticker,
        "name": ticker,
        "type": asset_type,
        "theme": theme,
        "riskLevel": risk,
        "isCore": asset_type.endswith("ETF") and ticker in {"VFV.TO", "XEQT.TO", "VEQT.TO", "XGRO.TO", "VOO", "VTI"},
    }


def timestamp() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
