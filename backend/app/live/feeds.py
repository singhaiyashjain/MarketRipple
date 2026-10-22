"""Feed registry + RSS/Atom parsing + English-only filtering.

Region tags drive the UI's  India | Global | All  switch.
All feeds below are English-language business/market feeds. Feed URLs change over time:
if one shows as "not responding" in the Live monitor, just edit/remove it here.
"""
from __future__ import annotations

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# (name, url, region)  region: "india" | "global"
FEEDS: list[tuple[str, str, str]] = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "india"),
    ("Livemint", "https://www.livemint.com/rss/markets", "india"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss", "india"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml", "india"),
    ("The Hindu BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss", "india"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "global"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147", "global"),
    ("The Guardian Business", "https://www.theguardian.com/business/rss", "global"),
    ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "global"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "global"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "global"),
    # Google News RSS: very reliable, keeps every region populated even when a single outlet feed breaks.
    # Each item carries its real publisher in <source>, which parse_feed() uses as the source name.
    ("Google News India Business", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en", "india"),
    ("Google News India Markets", "https://news.google.com/rss/search?q=RBI+OR+Sensex+OR+Nifty+OR+rupee+OR+%22crude+oil%22+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "india"),
    ("Google News World Business", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en", "global"),
    ("Google News World Economy", "https://news.google.com/rss/search?q=%22central+bank%22+OR+inflation+OR+tariffs+OR+oil+OR+sanctions+when:1d&hl=en-US&gl=US&ceid=US:en", "global"),
]

REGIONS = ("india", "global", "all")

_UA = {"User-Agent": "Mozilla/5.0 (FinPulse-AI live monitor)", "Accept": "application/rss+xml, application/xml, text/xml, */*"}
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# ----------------------------------------------------------------------------------------------
# News relevance: ONLY financial news and news the project's impact graph can use is kept.
#   FINANCIAL = unambiguous finance/economy term (STRONG), or several ambiguous ones (WEAK) together.
#   PROJECT   = the subset that touches what the graph models (oil, RBI/rates, rupee, inflation, banks...).
#   Entertainment / sport / crime / lifestyle stories are rejected unless the HEADLINE itself has a STRONG term.
# ----------------------------------------------------------------------------------------------
_STRONG = re.compile(
    r"\b(rbi|reserve bank|repo rate|reverse repo|interest rates?|rate (?:cut|cuts|hike|hikes|decision)|"
    r"monetary policy|mpc|inflation|disinflation|deflation|cpi|wpi|gdp|sensex|nifty|bse|nse|stock markets?|"
    r"stocks?|equit(?:y|ies)|wall street|dow jones|nasdaq|s&p 500|ftse|nikkei|hang seng|"
    r"bond yields?|treasury yields?|g-?sec|crude|brent|wti|opec|oil prices?|oil (?:supply|output|exports?|imports?)|"
    r"natural gas|lng|aviation fuel|atf|rupee|inr|usd/inr|forex|foreign exchange|exchange rates?|"
    r"dollar index|federal reserve|the fed|fomc|ecb|bank of england|bank of japan|central banks?|"
    r"tariffs?|trade war|trade deficit|current account|fiscal deficit|union budget|fiscal policy|"
    r"gst|ipo|earnings|quarterly results|net profit|market cap(?:italisation|italization)?|mutual funds?|"
    r"sebi|fiis?|fpis?|foreign portfolio|commodit(?:y|ies)|gold prices?|silver prices?|steel prices?|"
    r"fertili[sz]er|fuel prices?|petrol|diesel|supply chain|recession|economy|economic growth|"
    r"share prices?|shares? (?:fall|falls|fell|rise|rises|rose|jump|jumps|jumped|surge|surges|surged|slump|slumps|"
    r"slumped|drop|drops|dropped|plunge|plunges|plunged|climb|climbs|climbed|soar|soars|soared|tumble|tumbles|slide|slides)|"
    r"banking|nbfc|home loans?|emis?|deposit rates?|real estate|housing demand|cement demand|"
    r"indigo|interglobe|ongc|bpcl|hpcl|ioc|state bank of india|sbi|tcs|infosys|hdfc|icici|maruti|asian paints|"
    r"dlf|bajaj finance|ultratech|sun pharma|hindustan unilever)\b",
    re.I,
)
_WEAK = re.compile(
    r"\b(markets?|banks?|trade|trades|tax|taxes|profits?|revenue|supply|shortage|war|conflict|prices?|exports?|"
    r"imports?|growth|debt|loans?|investors?|investments?|business|merger|acquisition|layoffs?|sanctions?|"
    r"dollar|currency|shares?|budget|gas|rates?|funds?|economic|financial|finance|inflationary|subsidy|"
    r"deficit|bonds?|yields?|lender|lenders|billion|trillion|crore|lakh)\b",
    re.I,
)
_NON_FINANCIAL = re.compile(
    r"\b(cricket|ipl|football|soccer|premier league|champions league|tennis|wimbledon|olympics?|nba|nfl|fifa|"
    r"formula 1|f1 |bollywood|hollywood|movie|film|trailer|box office|actor|actress|celebrity|singer|album|"
    r"concert|netflix series|reality show|bigg boss|oscars?|grammys?|murder|arrested|stabbed|shot dead|rape|"
    r"kidnap|accident|earthquake|hurricane|cyclone|flood|weather|horoscope|recipe|fashion|skincare|diet|"
    r"zodiac|royal family|prince|princess|wedding|divorce|dating|viral video|tiktok|instagram|"
    r"lifestyle|travel guide|quiz|crossword)\b",
    re.I,
)
# what the impact graph actually models (a subset of FINANCIAL)
_PROJECT = re.compile(
    r"\b(crude|brent|wti|opec|oil prices?|oil (?:supply|output|exports?|imports?)|natural gas|lng|aviation fuel|atf|"
    r"petrol|diesel|fuel prices?|rbi|reserve bank|repo rate|interest rates?|rate (?:cut|cuts|hike|hikes|decision)|"
    r"monetary policy|mpc|rupee|inr|usd/inr|forex|foreign exchange|exchange rates?|dollar index|inflation|cpi|wpi|"
    r"food prices?|federal reserve|the fed|fomc|ecb|central banks?|tariffs?|trade war|sanctions?|import bill|"
    r"current account|fiscal deficit|gdp|sensex|nifty|fiis?|fpis?|foreign portfolio|bond yields?|g-?sec|banking|"
    r"banks?|lenders?|loan demand|nbfc|home loans?|emis?|deposit rates?|real estate|housing demand|cement demand|vehicle sales|fmcg|"
    r"indigo|interglobe|ongc|bpcl|hpcl|state bank of india|sbi|tcs|infosys|hdfc|icici|maruti|asian paints|dlf|"
    r"bajaj finance|ultratech|sun pharma|hindustan unilever)\b",
    re.I,
)


def classify(title: str, summary: str = "") -> dict:
    """{'financial': bool, 'project': bool} for one story. Strict on purpose: unrelated news is dropped."""
    title, summary = title or "", summary or ""
    both = f"{title} {summary}"
    strong_title = bool(_STRONG.search(title))
    strong = strong_title or bool(_STRONG.search(summary))
    weak_title = {m.group(0).lower() for m in _WEAK.finditer(title)}
    weak_all = weak_title | {m.group(0).lower() for m in _WEAK.finditer(summary)}
    if _NON_FINANCIAL.search(title) and not strong_title:
        financial = False
    elif strong:
        financial = True
    else:
        financial = bool(weak_title) and len(weak_all) >= 2
    project = financial and bool(_PROJECT.search(both))
    return {"financial": financial, "project": project}


def is_financial(title: str, summary: str = "") -> bool:
    return classify(title, summary)["financial"]


def is_relevant(text: str) -> bool:          # kept for older callers: text = "title summary"
    return is_financial(text)


def clean(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", text))).strip()


def is_english(text: str) -> bool:
    """True when (almost) every letter is Latin. Drops Hindi/Devanagari and other-script items."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if c.isascii() or "\u00c0" <= c <= "\u024f")
    return latin / len(letters) >= 0.95


def _parse_date(raw: str | None) -> datetime:
    if raw:
        try:
            d = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                d = None
        if d is not None:
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_feed(xml_bytes: bytes, source: str, region: str) -> list[dict]:
    """RSS 2.0 or Atom -> [{title, summary, source, link, published, region}] (English only)."""
    root = ET.fromstring(xml_bytes)
    out = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        f = {_local(c.tag): c for c in el}
        title = clean(f["title"].text) if "title" in f else ""
        summ = ""
        for k in ("description", "summary", "content"):
            if k in f and f[k].text:
                summ = clean(f[k].text)
                break
        link = ""
        if "link" in f:
            link = (f["link"].text or f["link"].attrib.get("href", "") or "").strip()
        raw_date = next((f[k].text for k in ("pubDate", "published", "updated", "date") if k in f and f[k].text), None)
        pub = _parse_date(raw_date)      # (an XML element with no children is falsy, so never chain them with `or`)
        if not title or not is_english(title) or (summ and not is_english(summ)):
            continue
        pub_name = clean(f["source"].text) if "source" in f and f["source"].text else ""
        if pub_name:                                   # aggregator feeds (Google News): real publisher + clean title
            source_name = pub_name
            suffix = f" - {pub_name}"
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
            if summ.startswith(title) or summ.lower().startswith(title.lower()):
                summ = ""                              # description is just the title + outlet name again
        else:
            source_name = source
        out.append({"title": title, "summary": summ[:600], "source": source_name, "link": link,
                    "published": pub.isoformat(), "region": region})
    return out


def fetch_feed(name: str, url: str, region: str, timeout: float = 8.0) -> list[dict]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:        # noqa: S310 (fixed https feed list)
        return parse_feed(r.read(), name, region)
