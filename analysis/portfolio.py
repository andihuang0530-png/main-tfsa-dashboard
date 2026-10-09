from __future__ import annotations

from typing import Any

from analysis.assets import candidate_lookup, default_currency, normalize_ticker
from analysis.scoring import analyze_security


def to_cad(amount: float, currency: str, settings: dict[str, Any]) -> float:
    if currency == "CAD":
        return amount
    return amount * float(settings.get("fxUsdCad", 1.37))


def from_cad(amount: float, currency: str, settings: dict[str, Any]) -> float:
    if currency == "CAD":
        return amount
    return amount / float(settings.get("fxUsdCad", 1.37))


def holding_action(holding: dict[str, Any], analysis: dict[str, Any], settings: dict[str, Any]) -> str:
    target_mode = bool(settings.get("useTargetAllocationMode", False))
    target_delta = holding.get("differenceFromTarget", 0) if target_mode else 0
    gain_pct = holding.get("unrealizedGainLossPct", 0)
    rsi = analysis.get("rsi") or 50
    risk = analysis.get("riskLevel", "Medium")
    asset_type = holding.get("type", "")
    below_ma200 = analysis.get("latestClose", 0) < analysis.get("ma200", 0)

    if asset_type.endswith("ETF"):
        if target_mode and target_delta >= 15:
            return "Rebalance"
        if analysis.get("actionLabel") in {"Strong Buy", "Buy", "Small Buy / Watch"}:
            return "Add"
        if target_mode and target_delta > 8:
            return "Do not add"
        return "Hold"

    if below_ma200 or risk == "High" and analysis.get("finalScore", 0) < 50:
        return "Sell alert"
    if target_mode and target_delta >= 10 and gain_pct >= 25 and rsi >= 70:
        return "Trim"
    if gain_pct >= 50 and target_mode and target_delta >= 5:
        return "Take profit"
    if target_mode and target_delta > 8:
        return "Do not add"
    if analysis.get("actionLabel") in {"Strong Buy", "Buy", "Small Buy / Watch"}:
        return "Add"
    return "Hold"


def risk_flags(holding: dict[str, Any], analysis: dict[str, Any], settings: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if settings.get("useTargetAllocationMode", False) and holding.get("differenceFromTarget", 0) > 5:
        flags.append("above target allocation")
    if analysis.get("rsi", 0) >= 70:
        flags.append("pullback risk elevated")
    if analysis.get("latestClose", 0) > analysis.get("ma50", 0) * 1.12:
        flags.append("overextended versus 50-day average")
    if analysis.get("forwardPe") and analysis["forwardPe"] > 35:
        flags.append("valuation risk elevated")
    if analysis.get("earningsRiskScore", 100) < 55:
        flags.append("earnings risk elevated")
    if not flags:
        flags.append("no major rule-based risk flag")
    return flags


def calculate_holdings(
    transactions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    watchlist: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    candidates_by_ticker = candidate_lookup(candidates)
    watch_by_ticker = {normalize_ticker(item["ticker"]): item for item in watchlist}
    lots: dict[str, dict[str, Any]] = {}

    for txn in sorted(transactions, key=lambda item: item.get("date", "")):
        ticker = normalize_ticker(txn.get("ticker", ""))
        metadata = candidates_by_ticker.get(ticker, {"ticker": ticker, "type": "US Stock", "name": ticker})
        currency = txn.get("currency") or default_currency(ticker, metadata.get("type"))
        shares = float(txn.get("shares", 0))
        price = float(txn.get("price", 0))
        amount = shares * price
        amount_cad = to_cad(amount, currency, settings)
        lot = lots.setdefault(
            ticker,
            {
                "ticker": ticker,
                "name": metadata.get("name", ticker),
                "type": metadata.get("type", "US Stock"),
                "currency": currency,
                "shares": 0.0,
                "costBasisLocal": 0.0,
                "costBasisCad": 0.0,
                "realizedGainLossCad": 0.0,
            },
        )
        if txn.get("action") == "Sell":
            if lot["shares"] <= 0:
                continue
            sell_shares = min(shares, lot["shares"])
            avg_cost_local = lot["costBasisLocal"] / lot["shares"] if lot["shares"] else 0
            avg_cost_cad = lot["costBasisCad"] / lot["shares"] if lot["shares"] else 0
            realized_cad = to_cad(sell_shares * price, currency, settings) - sell_shares * avg_cost_cad
            lot["shares"] -= sell_shares
            lot["costBasisLocal"] -= sell_shares * avg_cost_local
            lot["costBasisCad"] -= sell_shares * avg_cost_cad
            lot["realizedGainLossCad"] += realized_cad
        else:
            lot["shares"] += shares
            lot["costBasisLocal"] += amount
            lot["costBasisCad"] += amount_cad

    holdings: list[dict[str, Any]] = []
    total_value_cad = 0.0
    total_invested_cad = 0.0
    total_realized_cad = 0.0
    for ticker, lot in lots.items():
        if lot["shares"] <= 0.000001:
            continue
        quote = market_data.get(ticker, {"ticker": ticker, "dataStatus": "unavailable"})
        analysis = analyze_security(quote, watch_by_ticker.get(ticker, {}))
        current_price = quote.get("latestClose") or 0
        market_value_local = lot["shares"] * current_price
        market_value_cad = to_cad(market_value_local, lot["currency"], settings)
        total_value_cad += market_value_cad
        total_invested_cad += lot["costBasisCad"]
        total_realized_cad += lot["realizedGainLossCad"]
        target = watch_by_ticker.get(ticker, {}).get("targetAllocation") if settings.get("useTargetAllocationMode", False) else None
        avg_cost = lot["costBasisLocal"] / lot["shares"] if lot["shares"] else 0
        unrealized_cad = market_value_cad - lot["costBasisCad"]
        unrealized_pct = (unrealized_cad / lot["costBasisCad"] * 100) if lot["costBasisCad"] else 0
        holding = {
            "ticker": ticker,
            "name": lot["name"],
            "type": lot["type"],
            "shares": round(lot["shares"], 4),
            "averageCost": round(avg_cost, 2),
            "currency": lot["currency"],
            "totalInvestedCad": round(lot["costBasisCad"], 2),
            "currentPrice": round(current_price, 2),
            "currentMarketValueCad": round(market_value_cad, 2),
            "unrealizedGainLossCad": round(unrealized_cad, 2),
            "unrealizedGainLossPct": round(unrealized_pct, 1),
            "realizedGainLossCad": round(lot["realizedGainLossCad"], 2),
            "targetAllocation": float(target) if target is not None else None,
            "currentActionLabel": "",
            "riskFlags": [],
            "personalThesis": watch_by_ticker.get(ticker, {}).get("personalNote", ""),
            "notes": watch_by_ticker.get(ticker, {}).get("personalNote", ""),
            "analysis": analysis,
        }
        holdings.append(holding)

    for holding in holdings:
        weight = (holding["currentMarketValueCad"] / total_value_cad * 100) if total_value_cad else 0
        holding["portfolioWeight"] = round(weight, 1)
        holding["differenceFromTarget"] = round(weight - holding["targetAllocation"], 1) if holding["targetAllocation"] is not None else None
        holding["currentActionLabel"] = holding_action(holding, holding["analysis"], settings)
        holding["riskFlags"] = risk_flags(holding, holding["analysis"], settings)

    top_holding = max(holdings, key=lambda item: item.get("currentMarketValueCad", 0), default=None)
    total_unrealized = sum(item["unrealizedGainLossCad"] for item in holdings)
    summary = {
        "totalPortfolioValueCad": round(total_value_cad + float(settings.get("cashReserveCad", 0)), 2),
        "totalInvestedCad": round(total_invested_cad, 2),
        "unrealizedGainLossCad": round(total_unrealized, 2),
        "realizedGainLossCad": round(total_realized_cad, 2),
        "totalReturnPct": round(((total_unrealized + total_realized_cad) / total_invested_cad * 100) if total_invested_cad else 0, 1),
        "topHolding": top_holding["ticker"] if top_holding else "N/A",
        "targetAllocationMode": bool(settings.get("useTargetAllocationMode", False)),
        "aboveTargetCount": len([item for item in holdings if (item.get("differenceFromTarget") or 0) > 5]) if settings.get("useTargetAllocationMode", False) else 0,
        "trimSellAlertCount": len([item for item in holdings if item.get("currentActionLabel") in {"Trim", "Take profit", "Sell alert"}]),
        "cashReserveCad": float(settings.get("cashReserveCad", 0)),
    }
    return {"holdings": sorted(holdings, key=lambda item: item["currentMarketValueCad"], reverse=True), "summary": summary}
