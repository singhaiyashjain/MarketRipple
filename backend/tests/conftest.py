"""Test isolation: every test talks to an in-memory fake MongoDB (mongomock), never to a real database."""
import mongomock
import pytest
from app.graph import store
from app.recurrence import tracker


@pytest.fixture(autouse=True)
def _fake_mongo(monkeypatch):
    monkeypatch.setattr(store.settings, "mongodb_uri", "mongodb://test")
    monkeypatch.setattr(store, "_client_obj", mongomock.MongoClient())
    monkeypatch.setattr(store, "_retry_after", 0.0)
    monkeypatch.setattr(tracker, "_mongo", None)
