from __future__ import annotations

from copy import deepcopy
from typing import Any

from analysis.allocation import calculate_recommendations
from analysis.assets import (
    build_candidate_for_ticker,
    candidate_lookup,
    default_currency,
    is_supported_ticker,
    normalize_ticker,
    timestamp,
)
from analysis.exports import csv_from_rows, holdings_llm_text, recommendation_llm_text, watchlist_llm_text, weekly_pick_llm_text
from analysis.portfolio import calculate_holdings
from analysis.scoring import analyze_watchlist
from analysis.transactions import normalize_transaction
from analysis.weekly_picks import generate_weekly_picks
from providers.market.mock_provider import MockMarketProvider
from storage.json_store import (
    load_candidate_universe,
    load_settings,
    load_transactions,
    load_watchlist,
    save_candidate_universe,
    save_settings,
    save_transactions,
    save_watchlist,
    write_json,
)


def load_market_data() -> dict[str, dict[str, Any]]:
    candidates = load_candidate_universe()
    provider = MockMarketProvider()
    return provider.get_quotes(candidates)


def state() -> dict[str, Any]:
    settings = load_settings()
    settings.setdefault("useTargetAllocationMode", False)
    candidates = load_candidate_universe()
    watchlist = load_watchlist()
    transactions = load_transactions()
    market_data = load_market_data()
    watchlist_analysis = analyze_watchlist(watchlist, market_data)
    portfolio = calculate_holdings(transactions, candidates, market_data, watchlist, settings)
    recommendation = calculate_recommendations(watchlist_analysis, portfolio["holdings"], settings)
    weekly_picks = generate_weekly_picks(candidates, market_data, set(settings.get("dismissedWeeklyPicks", [])))
    write_json("watchlist_analysis.json", watchlist_analysis)
    write_json("holdings.json", portfolio)
    write_json("weekly_picks.json", weekly_picks)
    write_json("recommendation_snapshot.json", recommendation)
    return {
        "settings": settings,
        "candidateUniverse": candidates,
        "watchlist": watchlist,
        "watchlistAnalysis": watchlist_analysis,
        "transactions": transactions,
        "holdings": portfolio["holdings"],
        "portfolioSummary": portfolio["summary"],
        "recommendation": recommendation,
        "weeklyPicks": weekly_picks,
        "marketDataProvider": "mock",
    }


def summary_cards(app_state: dict[str, Any]) -> list[dict[str, Any]]:
    watchlist = app_state["watchlistAnalysis"]
    holdings = app_state["holdings"]
    recommendation = app_state["recommendation"]
    buy_candidates = [item for item in watchlist if item.get("actionLabel") in {"Strong Buy", "Buy", "Small Buy / Watch"}]
    avg_score = round(sum(item.get("finalScore", 0) for item in watchlist) / len(watchlist), 1) if watchlist else 0
    upcoming_earnings = len([item for item in watchlist if item.get("earningsRiskScore", 100) < 60])
    cad_etfs = len([item for item in watchlist if item.get("type") == "CAD ETF"])
    usd_tickers = len([item for item in watchlist if item.get("type") in {"US Stock", "US ETF"}])
    portfolio = app_state["portfolioSummary"]
    top_pick = recommendation.get("mainRecommendations", [{}])[0].get("ticker", "N/A") if recommendation.get("mainRecommendations") else "N/A"
    return [
        {"label": "Watchlist", "value": len(watchlist)},
        {"label": "Holdings", "value": len(holdings)},
        {"label": "Buy candidates", "value": len(buy_candidates)},
        {"label": "Top pick", "value": top_pick},
        {"label": "Avg final score", "value": avg_score},
        {"label": "High risk names", "value": len([item for item in watchlist if item.get("riskLevel") == "High"])},
        {"label": "Upcoming earnings", "value": upcoming_earnings},
        {"label": "CAD ETFs", "value": cad_etfs},
        {"label": "USD tickers", "value": usd_tickers},
        {"label": "Portfolio value", "value": f"CAD {portfolio.get('totalPortfolioValueCad', 0):,.2f}"},
        {"label": "Unrealized G/L", "value": f"CAD {portfolio.get('unrealizedGainLossCad', 0):,.2f}"},
    ]


def add_watchlist_ticker(ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    if not is_supported_ticker(ticker):
        raise ValueError("Unsupported ticker for this MVP.")
    watchlist = load_watchlist()
    if any(item["ticker"] == ticker for item in watchlist):
        return {"status": "already_exists", "ticker": ticker}
    candidates = load_candidate_universe()
    candidates_by_ticker = candidate_lookup(candidates)
    if ticker not in candidates_by_ticker:
        candidate = build_candidate_for_ticker(ticker)
        if candidate:
            candidates.append(candidate)
            save_candidate_universe(candidates)
    new_item = {
        "ticker": ticker,
        "personalNote": "",
        "manualDisabled": False,
        "addedAt": timestamp(),
    }
    if load_settings().get("useTargetAllocationMode", False):
        asset_type = candidates_by_ticker.get(ticker, build_candidate_for_ticker(ticker) or {}).get("type")
        new_item["targetAllocation"] = 10 if asset_type == "US Stock" else 25
    watchlist.append(new_item)
    save_watchlist(watchlist)
    return {"status": "added", "ticker": ticker}


def remove_watchlist_ticker(ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    watchlist = [item for item in load_watchlist() if item["ticker"] != ticker]
    save_watchlist(watchlist)
    return {"status": "removed", "ticker": ticker}


def update_watchlist_ticker(ticker: str, updates: dict[str, Any]) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    watchlist = load_watchlist()
    found = False
    for item in watchlist:
        if item["ticker"] == ticker:
            found = True
            if "personalNote" in updates:
                item["personalNote"] = str(updates["personalNote"])
            if "targetAllocation" in updates:
                item["targetAllocation"] = float(updates["targetAllocation"])
            if "manualDisabled" in updates:
                item["manualDisabled"] = bool(updates["manualDisabled"])
    if not found:
        raise ValueError("Ticker is not in watchlist.")
    save_watchlist(watchlist)
    return {"status": "updated", "ticker": ticker}


def dismiss_weekly_pick(ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    dismissed = set(load_settings().get("dismissedWeeklyPicks", []))
    dismissed.add(ticker)
    settings = load_settings()
    settings["dismissedWeeklyPicks"] = sorted(dismissed)
    save_settings(settings)
    return {"status": "dismissed", "ticker": ticker}


def calculate_with_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    app_state = state()
    settings = deepcopy(app_state["settings"])
    settings.update(overrides)
    return calculate_recommendations(app_state["watchlistAnalysis"], app_state["holdings"], settings)


def add_transaction(raw: dict[str, Any]) -> dict[str, Any]:
    ticker = normalize_ticker(raw.get("ticker", ""))
    candidates = load_candidate_universe()
    metadata = candidate_lookup(candidates).get(ticker) or build_candidate_for_ticker(ticker)
    if not metadata:
        raise ValueError("Unsupported ticker for this MVP.")
    transaction = normalize_transaction(raw, metadata)
    if not transaction["date"]:
        transaction["date"] = timestamp()
    if not transaction["currency"]:
        transaction["currency"] = default_currency(ticker, metadata.get("type"))
    transactions = load_transactions()
    transactions.append(transaction)
    save_transactions(transactions)
    return {"status": "added", "transaction": transaction}


def update_transaction(raw: dict[str, Any]) -> dict[str, Any]:
    txn_id = raw.get("id")
    if not txn_id:
        raise ValueError("Missing transaction id.")
    transactions = load_transactions()
    updated = False
    for index, txn in enumerate(transactions):
        if txn.get("id") == txn_id:
            metadata = candidate_lookup(load_candidate_universe()).get(normalize_ticker(raw.get("ticker", txn.get("ticker", ""))))
            transactions[index] = normalize_transaction({**txn, **raw}, metadata)
            updated = True
    if not updated:
        raise ValueError("Transaction not found.")
    save_transactions(transactions)
    return {"status": "updated", "id": txn_id}


def delete_transaction(txn_id: str) -> dict[str, Any]:
    transactions = [txn for txn in load_transactions() if txn.get("id") != txn_id]
    save_transactions(transactions)
    return {"status": "deleted", "id": txn_id}


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    settings.update(updates)
    save_settings(settings)
    return {"status": "updated", "settings": settings}


def update_candidate_universe(items: list[dict[str, Any]]) -> dict[str, Any]:
    clean = []
    for item in items:
        ticker = normalize_ticker(item.get("ticker", ""))
        if not ticker:
            continue
        clean.append({
            "ticker": ticker,
            "name": item.get("name", ticker),
            "type": item.get("type") or (build_candidate_for_ticker(ticker) or {}).get("type", "US Stock"),
            "theme": item.get("theme", "N/A"),
            "riskLevel": item.get("riskLevel", "Medium"),
            "isCore": bool(item.get("isCore", False)),
        })
    save_candidate_universe(clean)
    return {"status": "updated", "count": len(clean)}


def export_payload(kind: str, fmt: str) -> tuple[str, str]:
    app_state = state()
    if kind == "watchlist":
        rows = app_state["watchlistAnalysis"]
        if fmt == "csv":
            return csv_from_rows(rows), "text/csv"
        if fmt == "llm":
            return watchlist_llm_text(rows, app_state["settings"]), "text/plain"
        return __import__("json").dumps(rows, indent=2), "application/json"
    if kind == "holdings":
        rows = app_state["holdings"]
        if fmt == "csv":
            return csv_from_rows(rows), "text/csv"
        if fmt == "llm":
            return holdings_llm_text(rows, app_state["settings"]), "text/plain"
        return __import__("json").dumps(rows, indent=2), "application/json"
    if kind == "recommendation":
        if fmt == "llm":
            return recommendation_llm_text(app_state["recommendation"], app_state["holdings"], app_state["settings"]), "text/plain"
        return __import__("json").dumps(app_state["recommendation"], indent=2), "application/json"
    if kind == "weekly-pick":
        ticker = fmt.upper()
        row = next((item for item in app_state["weeklyPicks"] if item["ticker"] == ticker), None)
        if not row:
            raise ValueError("Weekly pick not found.")
        return weekly_pick_llm_text(row), "text/plain"
    raise ValueError("Unknown export kind.")
