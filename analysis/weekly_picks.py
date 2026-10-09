from __future__ import annotations

from typing import Any

from analysis.scoring import analyze_security


def generate_weekly_picks(candidates: list[dict[str, Any]], market_data: dict[str, dict[str, Any]], dismissed: set[str] | None = None) -> list[dict[str, Any]]:
    dismissed = dismissed or set()
    picks = []
    for candidate in candidates:
        ticker = candidate["ticker"]
        if ticker in dismissed:
            continue
        quote = market_data.get(ticker, {"ticker": ticker, "dataStatus": "unavailable"})
        analyzed = analyze_security(quote, {})
        score = analyzed.get("finalScore", 0)
        suggested_action = "Add to Watchlist" if score >= 65 else "Watch only" if score >= 55 else "Ignore for now"
        picks.append({
            "ticker": ticker,
            "name": candidate.get("name", ticker),
            "type": candidate.get("type", "N/A"),
            "theme": candidate.get("theme", "N/A"),
            "score": score,
            "riskLevel": candidate.get("riskLevel", "Medium"),
            "recentPerformanceSummary": f"1M {analyzed.get('return1m', 'N/A')}%, 3M {analyzed.get('return3m', 'N/A')}%, 1Y {analyzed.get('return1y', 'N/A')}%.",
            "newsSummary": analyzed.get("newsSummary") or "news unavailable",
            "reasonToResearch": analyzed.get("dashboardNote", "Quantitative profile supports review."),
            "keyRisks": analyzed.get("keyRisk", "Data unavailable."),
            "suggestedAction": suggested_action,
            "valuationRisk": analyzed.get("valuationScore", analyzed.get("costScore", "N/A")),
            "recentPerformance": analyzed.get("return3m", 0),
        })
    return sorted(picks, key=lambda row: row.get("score", 0), reverse=True)[:20]
