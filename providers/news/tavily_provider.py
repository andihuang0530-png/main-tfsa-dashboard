from __future__ import annotations

import os


class TavilyNewsProvider:
    name = "tavily"

    def configured(self) -> bool:
        return bool(os.getenv("TAVILY_API_KEY"))

    def get_news(self, ticker: str) -> list[dict]:
        if not self.configured():
            return []
        return []
