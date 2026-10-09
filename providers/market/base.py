from __future__ import annotations

from typing import Protocol


class MarketProvider(Protocol):
    name: str

    def get_quote(self, ticker: str, metadata: dict) -> dict:
        ...

    def get_quotes(self, candidates: list[dict]) -> dict[str, dict]:
        ...
