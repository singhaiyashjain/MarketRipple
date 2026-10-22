"""NLP entity linking: free-text event fields -> knowledge-graph node. OWNER: M3

Pure-python, no extra dependencies, runs offline (demo never depends on Wi-Fi).
Pipeline:  normalise -> tokenise -> stop-word removal -> light stemming -> domain synonym expansion
           -> TF-IDF vectors (sublinear tf) -> cosine similarity against one 'document' per node.
A node's document = its label (weighted x3) + sector + the explanations of the edges touching it,
so the graph's own knowledge helps the match (e.g. 'diesel' appears in the crude->diesel edge text).
Also: lexicon-based direction detection (surge / plunge ...) used when the extractor gives none.
"""
import math
import re
from collections import Counter
import networkx as nx

STOP = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "by", "as", "at", "is", "are", "its",
        "after", "amid", "over", "from", "with", "that", "this", "india", "indian", "price", "prices",
        "rise", "rises", "fall", "falls", "event", "shock", "change", "news"}

# query-expansion: surface word -> words that appear in our node labels (domain thesaurus)
SYNONYMS = {
    "jet": "aviation", "atf": "aviation fuel", "airline": "aviation", "airlines": "aviation",
    "petrol": "fuel", "gasoline": "fuel", "brent": "crude oil", "wti": "crude oil", "opec": "crude oil",
    "repo": "policy interest rate", "mpc": "policy interest rate", "rbi": "reserve bank india",
    "rupee": "usd inr", "inr": "usd inr", "dollar": "usd inr", "forex": "usd inr",
    "fii": "foreign portfolio flows", "fpi": "foreign portfolio flows", "fiis": "foreign portfolio flows",
    "institutional": "portfolio", "outflows": "flows", "inflows": "flows",
    "cpi": "inflation", "yields": "bond yields", "gsec": "bond yields",
    "software": "it services", "tech": "it services", "drug": "pharma", "drugs": "pharma",
    "housing": "real estate", "property": "real estate", "lenders": "banks", "banking": "banks",
    "sensex": "nifty", "equities": "nifty", "stocks": "nifty", "shipping": "logistics", "freight": "logistics",
}


def _stem(w: str) -> str:
    for suf in ("ings", "ing", "ies", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokenize(text: str, expand: bool = True) -> list[str]:
    text = (text or "").lower().replace("_", " ").replace("/", " ").replace("-", " ").replace("&", " and ")
    words = re.findall(r"[a-z]+", text)
    if expand:
        extra: list[str] = []
        for w in words:
            if w in SYNONYMS:
                extra += SYNONYMS[w].split()
        words += extra
    return [_stem(w) for w in words if w not in STOP and len(w) > 1]


class NodeLinker:
    def __init__(self, G: nx.DiGraph):
        self.ids: list[str] = []
        docs: list[list[str]] = []
        for nid, a in G.nodes(data=True):
            if a.get("type") == "event":
                continue
            toks = tokenize(a.get("label", ""), expand=False) * 3 + tokenize(a.get("sector") or "", expand=False)
            for _, _, d in list(G.in_edges(nid, data=True)) + list(G.out_edges(nid, data=True)):
                toks += tokenize(d.get("explanation", ""), expand=False)
            self.ids.append(nid)
            docs.append(toks)
        n = len(docs)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {t: (1 + math.log(c)) * self.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def link(self, text: str, threshold: float = 0.25) -> tuple[str | None, float]:
        q = self._vec(tokenize(text))
        best_id, best = None, 0.0
        for nid, v in zip(self.ids, self.vecs):
            s = sum(w * v.get(t, 0.0) for t, w in q.items())
            if s > best:
                best_id, best = nid, s
        return (best_id, round(best, 3)) if best >= threshold else (None, round(best, 3))


# ---------- direction detection (lexicon-based) ----------
UP = {"surge", "jump", "soar", "spike", "hike", "raise", "rally", "climb", "rise", "gain", "higher", "increase",
      "jumps", "surges", "soars", "spikes", "hikes", "raises", "rallies", "climbs", "rises", "gains", "increases",
      "depreciate", "depreciates", "weaken", "weakens"}
DOWN = {"fall", "drop", "plunge", "slump", "slash", "cut", "crash", "tumble", "decline", "lower", "dip", "decrease",
        "falls", "drops", "plunges", "slumps", "slashes", "cuts", "crashes", "tumbles", "declines", "dips",
        "decreases", "appreciate", "appreciates"}


def infer_direction(*texts: str | None) -> str | None:
    """'increase' / 'decrease' / None from a % sign or verb cues in the text."""
    joined = " ".join(t for t in texts if t).lower()
    m = re.search(r"([+-−–])\s*\d", joined)
    if m:
        return "decrease" if m.group(1) in "-−–" else "increase"
    words = set(re.findall(r"[a-z]+", joined))
    up, down = len(words & UP), len(words & DOWN)
    if up == down:
        return None
    return "increase" if up > down else "decrease"