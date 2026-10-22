"""Optional news-API source (NewsAPI.org). Enabled by NEWS_API_PROVIDER=newsapi + NEWS_API_KEY. English only."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from app.live.feeds import clean, is_english

BASE = "https://newsapi.org/v2"
GLOBAL_Q = 'economy OR "central bank" OR inflation OR oil OR tariffs OR "interest rates" OR currency OR sanctions'


def _get(path: str, params: dict, key: str) -> list[dict]:
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Api-Key": key, "User-Agent": "FinPulse-AI"})
    with urllib.request.urlopen(req, timeout=8) as r:              # noqa: S310
        body = json.loads(r.read().decode("utf-8"))
    if body.get("status") != "ok":
        raise RuntimeError(body.get("message", "news API error"))
    return body.get("articles", [])


def fetch(key: str) -> list[dict]:
    """India business headlines + worldwide economy headlines, English only."""
    rows = []
    jobs = [("top-headlines", {"country": "in", "category": "business", "pageSize": 30}, "india"),
            ("everything", {"q": GLOBAL_Q, "language": "en", "sortBy": "publishedAt", "pageSize": 30}, "global")]
    for path, params, region in jobs:
        for a in _get(path, params, key):
            title = clean(a.get("title"))
            summ = clean(a.get("description"))
            if not title or not is_english(title) or (summ and not is_english(summ)):
                continue
            rows.append({"title": title, "summary": summ[:600], "link": a.get("url") or "",
                         "source": (a.get("source") or {}).get("name") or "News API",
                         "published": a.get("publishedAt") or "", "region": region})
    return rows
