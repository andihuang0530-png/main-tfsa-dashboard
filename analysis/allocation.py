from __future__ import annotations

from typing import Any

from analysis.portfolio import from_cad


BUY_ACTIONS = {"Strong Buy", "Buy", "Small Buy / Watch"}
WEAKER_ACTIONS = {"Hold / Watch"}


def is_us_listed(item: dict[str, Any]) -> bool:
    return item.get("type") in {"US Stock", "US ETF"}


def is_above_target(ticker: str, holdings: list[dict[str, Any]]) -> tuple[bool, dict[str, Any] | None]:
    for holding in holdings:
        if holding["ticker"] == ticker:
            return (holding.get("differenceFromTarget") or 0) > 0, holding
    return False, None


def eligible_reason(item: dict[str, Any], settings: dict[str, Any], holdings: list[dict[str, Any]]) -> str | None:
    if item.get("dataStatus") != "ok":
        return "data unavailable"
    if item.get("manualDisabled"):
        return "manually disabled"
    if item.get("actionLabel") == "Avoid":
        return "action is Avoid"
    if not settings.get("allowUsdTickers", True) and is_us_listed(item):
        return "USD tickers disabled"
    if settings.get("useTargetAllocationMode", False):
        above_target, _ = is_above_target(item["ticker"], holdings)
        if settings.get("treatOverweightAsHardConstraint") and above_target:
            return "target allocation hard constraint"
    if settings.get("riskMode") == "Conservative":
        holding = next((row for row in holdings if row["ticker"] == item["ticker"]), None)
        high_concentration = holding and holding.get("portfolioWeight", 0) >= (35 if item.get("type") == "US Stock" else 50)
        if high_concentration and item.get("riskLevel") in {"Medium-High", "High"}:
            return "conservative concentration rule"
    return None


def allocation_cap(item: dict[str, Any], settings: dict[str, Any], risk_mode: str) -> float:
    if item.get("type") == "US Stock":
        if risk_mode == "Aggressive":
            cap = min(25, float(settings.get("maxSingleStockAllocation", 20)))
        elif risk_mode == "Conservative":
            cap = min(12, float(settings.get("maxSingleStockAllocation", 20)))
        else:
            cap = float(settings.get("maxSingleStockAllocation", 20))
        if item.get("riskLevel") == "High":
            cap = min(cap, float(settings.get("maxHighRiskStockAllocation", 10)))
        if item.get("riskLevel") == "Medium-High":
            cap = min(cap, max(10, float(settings.get("maxHighRiskStockAllocation", 10)) + 5))
        return cap
    if item.get("type", "").endswith("ETF"):
        cap = float(settings.get("maxSingleEtfAllocation", 50))
        if risk_mode == "Conservative" and item.get("isCore"):
            return min(cap, 55)
        if risk_mode == "Aggressive" and not item.get("isCore"):
            return min(cap, 35)
        return cap
    return 10


def ranking_score(item: dict[str, Any], settings: dict[str, Any], risk_mode: str) -> float:
    score = float(item.get("finalScore", 0))
    if settings.get("preferCadEtfs", True) and item.get("type") == "CAD ETF":
        score += 8
    if risk_mode == "Conservative":
        if item.get("isCore"):
            score += 10
        if item.get("type") == "US Stock":
            score -= 8
        if item.get("riskLevel") in {"Medium-High", "High"}:
            score -= 10
    elif risk_mode == "Aggressive":
        if item.get("theme") in {"AI", "AI infrastructure", "AI memory", "semiconductor"}:
            score += 5
        if item.get("riskLevel") == "High":
            score -= 4
    return score


def choose_candidates(watchlist_analysis: list[dict[str, Any]], holdings: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    risk_mode = settings.get("riskMode", "Balanced")
    eligible: list[dict[str, Any]] = []
    for item in watchlist_analysis:
        reason = eligible_reason(item, settings, holdings)
        if reason is None and item.get("actionLabel") in BUY_ACTIONS:
            enriched = dict(item)
            enriched["rankingScore"] = ranking_score(item, settings, risk_mode)
            eligible.append(enriched)
    if len(eligible) < int(settings.get("maxRecommendations", 5)):
        for item in watchlist_analysis:
            if item.get("actionLabel") not in WEAKER_ACTIONS:
                continue
            reason = eligible_reason(item, settings, holdings)
            if reason is None:
                enriched = dict(item)
                enriched["rankingScore"] = ranking_score(item, settings, risk_mode) - 10
                eligible.append(enriched)
    return sorted(eligible, key=lambda row: row["rankingScore"], reverse=True)


def distribute_amount(
    candidates: list[dict[str, Any]],
    amount: float,
    currency: str,
    settings: dict[str, Any],
    max_count: int,
) -> tuple[list[dict[str, Any]], float]:
    chosen = candidates[:max_count]
    if not chosen:
        return [], amount
    total_rank = sum(max(1, item["rankingScore"]) for item in chosen)
    allocations: list[dict[str, Any]] = []
    remaining = amount

    for item in chosen:
        raw_pct = max(1, item["rankingScore"]) / total_rank * 100
        cap = allocation_cap(item, settings, settings.get("riskMode", "Balanced"))
        pct = min(raw_pct, cap)
        suggested = round(amount * pct / 100, 2)
        remaining -= suggested
        allocations.append({**item, "suggestedAllocationPct": round(pct, 1), "suggestedAmount": suggested})

    if remaining > 0.01 and allocations:
        for row in allocations:
            cap = allocation_cap(row, settings, settings.get("riskMode", "Balanced"))
            room_pct = max(0, cap - row["suggestedAllocationPct"])
            if room_pct <= 0:
                continue
            add = min(remaining, amount * room_pct / 100)
            row["suggestedAmount"] = round(row["suggestedAmount"] + add, 2)
            row["suggestedAllocationPct"] = round(row["suggestedAmount"] / amount * 100, 1)
            remaining -= add
            if remaining <= 0.01:
                break

    for row in allocations:
        price_in_input_currency = row.get("latestClose") or 0
        if row.get("currency") != currency:
            if currency == "CAD" and row.get("currency") == "USD":
                price_in_input_currency = row["latestClose"] * float(settings.get("fxUsdCad", 1.37))
            elif currency == "USD" and row.get("currency") == "CAD":
                price_in_input_currency = from_cad(row["latestClose"], "USD", settings)
        if price_in_input_currency <= 0:
            shares = 0
        elif settings.get("allowFractionalShares", True):
            shares = round(row["suggestedAmount"] / price_in_input_currency, 4)
        else:
            shares = int(row["suggestedAmount"] / price_in_input_currency)
            row["suggestedAmount"] = round(shares * price_in_input_currency, 2)
        row["estimatedShares"] = shares
        row["suggestedCurrency"] = currency

    used = sum(row["suggestedAmount"] for row in allocations)
    return allocations, round(max(0, amount - used), 2)


def holding_contexts(recommended: list[dict[str, Any]], holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contexts = []
    holdings_by_ticker = {item["ticker"]: item for item in holdings}
    for item in recommended:
        holding = holdings_by_ticker.get(item["ticker"])
        if not holding:
            continue
        contexts.append({
            "ticker": item["ticker"],
            "currentShares": holding.get("shares", 0),
            "currentPortfolioWeight": holding.get("portfolioWeight", 0),
            "unrealizedGainLossPct": holding.get("unrealizedGainLossPct", 0),
            "unrealizedGainLossCad": holding.get("unrealizedGainLossCad", 0),
            "note": (
                f"Already held; current portfolio weight is {holding.get('portfolioWeight', 0)}%. "
                "This is shown as context only and does not block the recommendation."
            ),
        })
    return contexts


def portfolio_warnings(recommended: list[dict[str, Any]], holdings: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    if not settings.get("useTargetAllocationMode", False):
        return []
    warnings = []
    holdings_by_ticker = {item["ticker"]: item for item in holdings}
    for item in recommended:
        holding = holdings_by_ticker.get(item["ticker"])
        if not holding:
            continue
        above_target_pp = holding.get("differenceFromTarget") or 0
        if above_target_pp <= 0:
            continue
        warnings.append({
            "ticker": item["ticker"],
            "currentPortfolioWeight": holding.get("portfolioWeight", 0),
            "targetAllocation": holding.get("targetAllocation", item.get("targetAllocation", 0)),
            "aboveTargetPp": round(above_target_pp, 1),
            "unrealizedGainLossPct": holding.get("unrealizedGainLossPct", 0),
            "unrealizedGainLossCad": holding.get("unrealizedGainLossCad", 0),
            "warningMessage": (
                f"{item['ticker']} currently represents {holding.get('portfolioWeight', 0)}% of your portfolio, "
                f"above your target allocation of {holding.get('targetAllocation', item.get('targetAllocation', 0))}% "
                f"by {round(above_target_pp, 1)} percentage points. Target allocation mode is on, so this is shown as allocation context."
            ),
            "whyItMatters": "Target allocation mode helps compare the current portfolio to user-defined targets. It does not predict exact tops or bottoms.",
        })
    return warnings


def plan_b_allocations(
    main_allocations: list[dict[str, Any]],
    skipped_tickers: list[str],
    all_candidates: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    skip_set = set(skipped_tickers)
    if not skip_set:
        return []
    skipped_amount = sum(item["suggestedAmount"] for item in main_allocations if item["ticker"] in skip_set)
    if skipped_amount <= 0:
        return []

    held_by_ticker = {item["ticker"]: item for item in holdings}
    existing_main = {item["ticker"] for item in main_allocations if item["ticker"] not in skip_set}
    alternatives = []
    for item in all_candidates:
        if item["ticker"] in skip_set:
            continue
        reason = eligible_reason(item, settings, holdings)
        if reason is not None:
            continue
        holding = held_by_ticker.get(item["ticker"])
        if settings.get("useTargetAllocationMode", False) and holding and (holding.get("differenceFromTarget") or 0) > 0:
            continue
        preference = 0
        if item.get("isCore"):
            preference += 50
        if settings.get("preferCadEtfs", True) and item.get("type") == "CAD ETF":
            preference += 30
        if item.get("type", "").endswith("ETF"):
            preference += 20
        if item["ticker"] in existing_main:
            preference += 10
        alternatives.append({**item, "rankingScore": ranking_score(item, settings, settings.get("riskMode", "Balanced")) + preference})

    alternatives.sort(key=lambda row: row["rankingScore"], reverse=True)
    if not alternatives:
        return [{"ticker": "Cash reserve", "name": "Cash reserve", "suggestedAmount": round(skipped_amount, 2), "reason": "No suitable alternative was available for the skipped ticker."}]

    chosen = alternatives[: min(3, len(alternatives))]
    total_score = sum(max(1, item["rankingScore"]) for item in chosen)
    return [
        {
            "ticker": item["ticker"],
            "name": item.get("name", item["ticker"]),
            "type": item.get("type", "N/A"),
            "suggestedAmount": round(skipped_amount * max(1, item["rankingScore"]) / total_score, 2),
            "reason": "Redistributed because you skipped a main recommendation.",
        }
        for item in chosen
    ]


def recommendation_summary(
    allocations: list[dict[str, Any]],
    holding_context: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    plan_b: list[dict[str, Any]],
    settings: dict[str, Any],
    remaining_cash: float,
) -> str:
    currency = settings.get("investmentCurrency", "CAD")
    amount = settings.get("investmentAmount", 0)
    if not allocations:
        return "No strong buy candidates today. Consider holding cash or adding only to core ETF positions."

    buys = ", ".join(f"{row['ticker']} {currency} {row['suggestedAmount']:.2f}" for row in allocations)
    context_text = "No current holdings overlap with this recommendation."
    if holding_context:
        context_text = "Holding context: " + "; ".join(item["note"] for item in holding_context)
    warning_text = ""
    if settings.get("useTargetAllocationMode", False) and warnings:
        warning_text = " Target allocation notes: " + "; ".join(item["warningMessage"] for item in warnings)
    plan_b_text = "No Plan B needed."
    if plan_b:
        plan_b_text = "Plan B for skipped tickers: " + ", ".join(f"{item['ticker']} {currency} {item['suggestedAmount']:.2f}" for item in plan_b)
    cash_text = f"Remaining cash: {currency} {remaining_cash:.2f}." if remaining_cash else "Holding extra cash is optional rather than required by the current rule set."
    return (
        f"For this week, the rule-based model allocates {currency} {float(amount):.2f} across {buys}. "
        f"{context_text}{warning_text} {plan_b_text} {cash_text}"
    )


def calculate_recommendations(
    watchlist_analysis: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    amount = float(settings.get("investmentAmount", 0) or 0)
    currency = settings.get("investmentCurrency", "CAD")
    max_count = int(settings.get("maxRecommendations", 5))
    candidates = choose_candidates(watchlist_analysis, holdings, settings)
    main, remaining_cash = distribute_amount(candidates, amount, currency, settings, max_count)
    skipped_tickers = [str(ticker).upper() for ticker in settings.get("skippedTickers", [])]
    holding_context = holding_contexts(main, holdings)
    warnings = portfolio_warnings(main, holdings, settings)
    plan_b = plan_b_allocations(main, skipped_tickers, candidates, holdings, settings)
    summary = recommendation_summary(main, holding_context, warnings, plan_b, settings, remaining_cash)
    return {
        "mainRecommendations": [
            {
                **row,
                "rank": idx + 1,
                "holdingContext": next((context for context in holding_context if context["ticker"] == row["ticker"]), None),
                "portfolioContextStatus": "Already held" if any(context["ticker"] == row["ticker"] for context in holding_context) else "Not held",
                "portfolioWarningStatus": "Target note" if any(w["ticker"] == row["ticker"] for w in warnings) else "Context only",
            }
            for idx, row in enumerate(main)
        ],
        "holdingContext": holding_context,
        "portfolioWarnings": warnings,
        "planB": plan_b,
        "skippedTickers": skipped_tickers,
        "remainingCash": remaining_cash,
        "summary": summary,
        "noBuy": len(main) == 0,
    }
