from __future__ import annotations


class RssNewsProvider:
    name = "rss"

    def get_news(self, ticker: str) -> list[dict]:
        return []
