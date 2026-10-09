from __future__ import annotations

from typing import Protocol


class NewsProvider(Protocol):
    name: str

    def get_news(self, ticker: str) -> list[dict]:
        ...
