from __future__ import annotations

from datetime import date, datetime
from typing import Any


ACTION_COLORS = {
    "Strong Buy": "green",
    "Buy": "blue",
    "Small Buy / Watch": "yellow",
    "Hold / Watch": "gray",
    "Avoid": "red",
}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def score_from_range(value: float | None, good: float, bad: float) -> float:
    if value is None:
        return 50
    if good == bad:
        return 50
    ratio = (value - bad) / (good - bad)
    return clamp(ratio * 100)


def action_from_score(score: float) -> str:
    if score >= 75:
        return "Strong Buy"
    if score >= 65:
        return "Buy"
    if score >= 58:
        return "Small Buy / Watch"
    if score >= 50:
        return "Hold / Watch"
    return "Avoid"


def risk_penalty(risk_level: str) -> float:
    return {
        "Low": 4,
        "Medium": 0,
        "Medium-High": -8,
        "High": -16,
    }.get(risk_level, 0)


def stock_scores(quote: dict[str, Any]) -> dict[str, float]:
    trend = (
        score_from_range(quote.get("return3m"), 20, -10) * 0.30
        + score_from_range(quote.get("return6m"), 30, -15) * 0.30
        + score_from_range(quote.get("return1y"), 45, -20) * 0.20
        + score_from_range(quote.get("latestClose", 0) - quote.get("ma200", 0), quote.get("latestClose", 1) * 0.18, -quote.get("latestClose", 1) * 0.12) * 0.20
    )
    risk = (
        score_from_range(quote.get("volatility"), 12, 48) * 0.35
        + score_from_range(quote.get("rsi"), 55, 82) * 0.20
        + score_from_range(quote.get("beta"), 0.8, 2.0) * 0.25
        + (60 + risk_penalty(quote.get("riskLevel", "Medium"))) * 0.20
    )
    valuation = (
        score_from_range(quote.get("forwardPe"), 20, 55) * 0.55
        + score_from_range(quote.get("peRatio"), 22, 70) * 0.45
    )
    growth = (
        score_from_range(quote.get("revenueGrowth"), 30, 0) * 0.35
        + score_from_range(quote.get("epsGrowth"), 35, -5) * 0.35
        + score_from_range(quote.get("profitMargin"), 35, 5) * 0.30
    )
    news_event = 64 if quote.get("newsSummary") and "unavailable" not in quote.get("newsSummary", "").lower() else 50
    earnings_risk = 65
    earnings_date = quote.get("earningsDate")
    if earnings_date:
        try:
            days = (datetime.fromisoformat(earnings_date).date() - date.today()).days
            if 0 <= days <= 14:
                earnings_risk = 42
            elif 15 <= days <= 30:
                earnings_risk = 55
        except ValueError:
            earnings_risk = 55

    return {
        "trendScore": round(clamp(trend), 1),
        "riskScore": round(clamp(risk), 1),
        "valuationScore": round(clamp(valuation), 1),
        "growthProfitabilityScore": round(clamp(growth), 1),
        "newsEventScore": round(clamp(news_event), 1),
        "earningsRiskScore": round(clamp(earnings_risk), 1),
    }


def etf_scores(quote: dict[str, Any]) -> dict[str, float]:
    exposure = 82 if quote.get("isCore") else 70
    if quote.get("theme") in {"semiconductor", "AI", "AI infrastructure"}:
        exposure += 4
    cost = score_from_range(quote.get("expenseRatio"), 0.08, 0.75)
    liquidity = 72 if quote.get("aum") else 55
    risk_trend = (
        score_from_range(quote.get("return6m"), 20, -10) * 0.35
        + score_from_range(quote.get("return1y"), 30, -15) * 0.30
        + score_from_range(quote.get("volatility"), 12, 35) * 0.20
        + score_from_range(quote.get("rsi"), 58, 80) * 0.15
    )
    tracking = 80 if quote.get("isCore") else 66
    return {
        "exposureScore": round(clamp(exposure), 1),
        "costScore": round(clamp(cost), 1),
        "liquidityScore": round(clamp(liquidity), 1),
        "riskTrendScore": round(clamp(risk_trend), 1),
        "trackingQualityScore": round(clamp(tracking), 1),
    }


def final_stock_score(scores: dict[str, float]) -> float:
    return round(
        scores["trendScore"] * 0.25
        + scores["riskScore"] * 0.20
        + scores["valuationScore"] * 0.20
        + scores["growthProfitabilityScore"] * 0.20
        + scores["newsEventScore"] * 0.10
        + scores["earningsRiskScore"] * 0.05,
        1,
    )


def final_etf_score(scores: dict[str, float]) -> float:
    return round(
        scores["exposureScore"] * 0.30
        + scores["costScore"] * 0.20
        + scores["liquidityScore"] * 0.15
        + scores["riskTrendScore"] * 0.25
        + scores["trackingQualityScore"] * 0.10,
        1,
    )


def advisory_note(item: dict[str, Any]) -> tuple[str, str]:
    if item["type"].endswith("ETF"):
        if item.get("isCore"):
            return "Core ETF suitable for scheduled long-term contributions.", "Market drawdowns can still affect broad ETFs."
        return "ETF gives diversified exposure to the selected theme.", "Sector concentration can raise pullback risk."
    if item.get("rsi", 0) >= 70:
        return "Strong trend and quality profile, but entry discipline matters.", "Pullback risk elevated after a strong move."
    if item.get("forwardPe") and item["forwardPe"] > 35:
        return "Growth profile remains attractive for watchlist review.", "Valuation risk elevated."
    return "Quantitative profile supports continued research.", "Single-stock thesis needs periodic review."


def analyze_security(quote: dict[str, Any], watch_item: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(quote)
    watch_item = watch_item or {}
    if quote.get("dataStatus") != "ok":
        result.update({
            "finalScore": 0,
            "actionLabel": "Avoid",
            "dashboardNote": "Data unavailable.",
            "keyRisk": "Data unavailable.",
        })
        return result

    if quote["type"].endswith("ETF"):
        scores = etf_scores(quote)
        final = final_etf_score(scores)
    else:
        scores = stock_scores(quote)
        final = final_stock_score(scores)

    note, key_risk = advisory_note({**quote, "finalScore": final})
    result.update(scores)
    result.update({
        "finalScore": final,
        "actionLabel": action_from_score(final),
        "dashboardNote": note,
        "keyRisk": key_risk,
        "personalNote": watch_item.get("personalNote", ""),
        "targetAllocation": watch_item.get("targetAllocation"),
        "manualDisabled": bool(watch_item.get("manualDisabled", False)),
    })
    return result


def analyze_watchlist(watchlist: list[dict[str, Any]], market_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    analyzed = []
    for item in watchlist:
        ticker = item["ticker"].upper()
        quote = market_data.get(ticker, {"ticker": ticker, "dataStatus": "unavailable"})
        analyzed.append(analyze_security(quote, item))
    return sorted(analyzed, key=lambda row: row.get("finalScore", 0), reverse=True)
