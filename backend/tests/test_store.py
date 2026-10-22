import pytest
from app.graph import store


class _FakeCollection:
    def __init__(self):
        self.docs, self.calls = {}, 0

    def insert_one(self, doc):
        self.calls += 1
        _id = f"id{len(self.docs) + 1}"
        self.docs[_id] = doc
        return type("R", (), {"inserted_id": _id})()

    def find_one(self, q):
        return self.docs.get(q["_id"])


@pytest.fixture
def fake(monkeypatch):
    col = _FakeCollection()
    monkeypatch.setattr(store, "_collection", lambda: col)
    monkeypatch.setattr(store, "_to_id", lambda x: x)       # real one needs bson (ships with pymongo)
    monkeypatch.setattr(store, "_retry_after", 0.0)
    return col


def test_save_and_load_roundtrip(fake):
    aid = store.save_analysis({"mode": "live", "paths": [{"id": "p1", "strength": 0.5}]})
    assert isinstance(aid, str)
    assert store.load_analysis(aid)["paths"][0]["strength"] == 0.5


def test_unknown_id_raises_keyerror(fake):
    with pytest.raises(KeyError):
        store.load_analysis("does-not-exist")


def test_without_uri_saving_is_disabled(monkeypatch):
    monkeypatch.setattr(store.settings, "mongodb_uri", "")
    monkeypatch.setattr(store, "_retry_after", 0.0)
    with pytest.raises(RuntimeError):
        store.save_analysis({"a": 1})
    monkeypatch.setattr(store, "_retry_after", 0.0)


def test_backoff_after_failure(monkeypatch):
    calls = []

    def boom():
        calls.append(1)
        raise ConnectionError("db down")
    monkeypatch.setattr(store, "_collection", boom)
    monkeypatch.setattr(store, "_retry_after", 0.0)
    with pytest.raises(ConnectionError):
        store.save_analysis({"a": 1})
    with pytest.raises(RuntimeError):                         # second call skipped, DB not touched again
        store.save_analysis({"a": 1})
    assert len(calls) == 1
    monkeypatch.setattr(store, "_retry_after", 0.0)

def test_real_store_roundtrip_with_fake_mongo():
    """conftest swaps in mongomock: exercises the REAL store code (ObjectId ids, copy, created_at stripped)."""
    doc = {"mode": "live", "paths": [{"id": "p1", "strength": 0.5}]}
    aid = store.save_analysis(doc)
    assert isinstance(aid, str) and len(aid) == 24 and "_id" not in doc
    got = store.load_analysis(aid)
    assert got == doc
    with pytest.raises(KeyError):
        store.load_analysis("not-an-object-id")
    with pytest.raises(KeyError):
        store.load_analysis("0" * 24)
