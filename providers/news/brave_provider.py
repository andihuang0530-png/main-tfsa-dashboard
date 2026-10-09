from __future__ import annotations

import os


class BraveNewsProvider:
    name = "brave"

    def configured(self) -> bool:
        return bool(os.getenv("BRAVE_SEARCH_API_KEY"))

    def get_news(self, ticker: str) -> list[dict]:
        if not self.configured():
            return []
        return []
