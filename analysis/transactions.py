from __future__ import annotations

from typing import Any
from uuid import uuid4

from analysis.assets import default_currency, normalize_ticker


def normalize_transaction(raw: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    ticker = normalize_ticker(raw.get("ticker", ""))
    action = raw.get("action", "Buy").title()
    asset_type = metadata.get("type") if metadata else None
    return {
        "id": raw.get("id") or f"txn-{uuid4().hex[:10]}",
        "date": raw.get("date"),
        "ticker": ticker,
        "action": "Sell" if action == "Sell" else "Buy",
        "shares": float(raw.get("shares") or 0),
        "price": float(raw.get("price") or 0),
        "currency": raw.get("currency") or default_currency(ticker, asset_type),
        "notes": raw.get("notes", ""),
    }


def transaction_total(transaction: dict[str, Any]) -> float:
    return round(float(transaction.get("shares", 0)) * float(transaction.get("price", 0)), 2)
