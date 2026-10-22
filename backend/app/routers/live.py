"""Live monitor API: /api/live/*  and  /api/headlines.   Region filter: india | global | all."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.live.monitor import monitor

router = APIRouter()


class ReplayBody(BaseModel):
    enabled: bool


@router.get("/live/status")
def live_status():
    return monitor.status()


@router.get("/live/events")
def live_events(region: str = "all", limit: int = 30):
    return monitor.history(region, min(max(limit, 1), 40))


@router.get("/live/events/{version}")
def live_event(version: int):
    ev = monitor.event(version)
    if ev is None:
        raise HTTPException(status_code=404, detail="event aged out of history")
    return ev


@router.post("/live/poll")
def live_poll():
    return monitor.poll()


@router.post("/live/fire")
def live_fire():
    ev = monitor.fire_next()
    if ev is None:
        raise HTTPException(status_code=500, detail="could not analyse saved event")
    return {"version": ev["version"]}


@router.post("/live/replay")
def live_replay(body: ReplayBody):
    monitor.set_replay(body.enabled)
    return {"replay": monitor.replay}


@router.get("/headlines")
def headlines(region: str = "all", limit: int = 60):
    return monitor.get_headlines(region, min(max(limit, 1), 100))
