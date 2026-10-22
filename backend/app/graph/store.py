"""MongoDB persistence for analyses (optional - the app works without it). OWNER: M3

Set MONGODB_URI (and optionally MONGODB_DB) in .env. Leave MONGODB_URI empty to disable saving.
pymongo is imported lazily, so the API and the tests start even if MongoDB / pymongo is absent.
If the database is unreachable we back off for 60 s instead of delaying every request.
"""
import json
import time
from datetime import datetime, timezone
from app.config import settings

_client = None
_retry_after = 0.0          # monotonic time before which we do not try MongoDB again
BACKOFF_S = 60


def _collection():
    global _client
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI is not set - analyses are not saved")
    from pymongo import MongoClient
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
    return _client[settings.mongodb_db]["analyses"]


def _to_id(analysis_id: str):
    """Turn the id string from the URL into a Mongo ObjectId (KeyError if it is not a valid id)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        return ObjectId(analysis_id)
    except (InvalidId, TypeError):
        raise KeyError(analysis_id)


def save_analysis(response_json: dict) -> str:
    """Store one analysis response; returns its id as a string."""
    global _retry_after
    if time.monotonic() < _retry_after:
        raise RuntimeError("MongoDB unavailable recently - skipping save")
    try:
        doc = {"created_at": datetime.now(timezone.utc),
               "response": json.loads(json.dumps(response_json))}      # guarantees BSON-safe plain data
        return str(_collection().insert_one(doc).inserted_id)
    except Exception:
        _retry_after = time.monotonic() + BACKOFF_S
        raise


def load_analysis(analysis_id: str) -> dict:
    doc = _collection().find_one({"_id": _to_id(analysis_id)})
    if doc is None:
        raise KeyError(analysis_id)
    return doc["response"]