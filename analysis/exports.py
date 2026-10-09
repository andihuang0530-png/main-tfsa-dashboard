from __future__ import annotations

import csv
import io
import json
from typing import Any


def csv_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    flattened = []
    for row in rows:
        flattened.append({key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(flattened[0].keys()))
    writer.writeheader()
    writer.writerows(flattened)
    return output.getvalue()


def recommendation_llm_text(recommendation: dict[str, Any], holdings: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    lines = [
        "Portfolio context:",
        f"- Account type: {settings.get('accountType', 'TFSA')}",
        f"- Goal: {settings.get('goal', 'long-term investing')}",
        f"- Style: {settings.get('style', 'weekly investing / dollar-cost averaging')}",
        f"- Risk mode: {settings.get('riskMode')}",
        f"- Prefer CAD ETFs: {settings.get('preferCadEtfs')}",
        f"- Allow USD tickers: {settings.get('allowUsdTickers')}",
        "",
        "Current recommendation:",
        f"- Investment amount: {settings.get('investmentCurrency', 'CAD')} {settings.get('investmentAmount')}",
        "- Main recommended tickers:",
    ]
    for row in recommendation.get("mainRecommendations", []):
        context = row.get("holdingContext")
        held_text = ""
        if context:
            held_text = f" - Already held; current portfolio weight {context.get('currentPortfolioWeight')}%; unrealized gain/loss {context.get('unrealizedGainLossPct')}%"
        lines.append(
            f"  {row['rank']}. {row['ticker']} - {row['suggestedCurrency']} {row['suggestedAmount']} - "
            f"{row.get('dashboardNote', '')} - Score {row.get('finalScore')} - Trend {row.get('trendScore', row.get('riskTrendScore', 'N/A'))} - "
            f"Risk {row.get('riskLevel')} - Valuation/cost {row.get('valuationScore', row.get('costScore', 'N/A'))} - "
            f"ETF quality {row.get('trackingQualityScore', 'N/A')}{held_text}"
        )
    if recommendation.get("holdingContext"):
        lines.extend(["", "Current holding context:"])
        for context in recommendation["holdingContext"]:
            lines.append(
                f"- {context['ticker']} is already held and currently represents {context['currentPortfolioWeight']}% of the portfolio. "
                "This is shown as context only and does not block the recommendation."
            )
    if settings.get("useTargetAllocationMode") and recommendation.get("portfolioWarnings"):
        lines.extend(["", "Target allocation notes:"])
        for warning in recommendation["portfolioWarnings"]:
            lines.append(f"- {warning['warningMessage']}")
    if recommendation.get("planB"):
        lines.extend(["", "Plan B for skipped tickers:"])
        for item in recommendation["planB"]:
            lines.append(f"- Add {settings.get('investmentCurrency', 'CAD')} {item['suggestedAmount']} to {item['ticker']}")
    lines.extend(["", "Current holdings:"])
    for holding in holdings:
        lines.append(
            f"- {holding['ticker']} - {holding['shares']} shares - avg cost {holding['currency']} {holding['averageCost']} - "
            f"current price {holding['currency']} {holding['currentPrice']} - unrealized gain {holding['unrealizedGainLossPct']}% - "
            f"current weight {holding['portfolioWeight']}% - action {holding['currentActionLabel']}"
        )
    lines.extend([
        "",
        "Question for LLM:",
        "Please analyze whether this weekly allocation is reasonable. Should I follow the main recommendation, use Plan B, hold cash, or adjust the allocation based on my long-term TFSA investing goal?",
    ])
    return "\n".join(lines)


def holdings_llm_text(holdings: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    lines = [
        "Portfolio holdings summary for LLM review:",
        f"- Account type: {settings.get('accountType', 'TFSA')}",
        f"- Goal: {settings.get('goal', 'long-term investing')}",
        f"- Risk mode: {settings.get('riskMode')}",
        "",
        "Current holdings:",
    ]
    for holding in holdings:
        lines.append(
            f"- {holding['ticker']} - shares {holding['shares']} - average cost {holding['currency']} {holding['averageCost']} - "
            f"current price {holding['currency']} {holding['currentPrice']} - unrealized gain/loss CAD {holding['unrealizedGainLossCad']} "
            f"({holding['unrealizedGainLossPct']}%) - weight {holding['portfolioWeight']}% - "
            f"model action {holding['currentActionLabel']} - risk flags: {', '.join(holding['riskFlags'])} - notes: {holding.get('notes', '')}"
        )
    lines.extend([
        "",
        "Question for LLM:",
        "Please review whether I should hold, add, trim, or sell any of these positions based on current data and my long-term TFSA investing goal.",
    ])
    return "\n".join(lines)


def watchlist_llm_text(rows: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    lines = [
        "Watchlist analysis for LLM review:",
        f"- Goal: {settings.get('goal', 'long-term investing')}",
        f"- Risk mode: {settings.get('riskMode')}",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['ticker']} ({row.get('type')}) - score {row.get('finalScore')} - action {row.get('actionLabel')} - "
            f"risk {row.get('riskLevel')} - price {row.get('currency')} {row.get('latestClose')} - "
            f"note: {row.get('dashboardNote')} - key risk: {row.get('keyRisk')} - personal note: {row.get('personalNote', '')}"
        )
    return "\n".join(lines)


def weekly_pick_llm_text(row: dict[str, Any]) -> str:
    return "\n".join([
        "Weekly pick research candidate:",
        f"- Ticker: {row.get('ticker')}",
        f"- Name: {row.get('name')}",
        f"- Type: {row.get('type')}",
        f"- Theme: {row.get('theme')}",
        f"- Score: {row.get('score')}",
        f"- Risk level: {row.get('riskLevel')}",
        f"- Performance: {row.get('recentPerformanceSummary')}",
        f"- News summary: {row.get('newsSummary')}",
        f"- Reason to research: {row.get('reasonToResearch')}",
        f"- Key risks: {row.get('keyRisks')}",
        "Question for LLM: Should I add this candidate to my TFSA watchlist for long-term research, watch only, or ignore for now?",
    ])
