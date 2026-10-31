"""FastAPI entrypoint. Run: uvicorn app.main:app --reload   OWNER: M3"""
from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import users
from app.auth.deps import gate
from app.config import settings
from app.live.monitor import monitor
from app.routers import admin, analyze, auth, chat, live, recurrence, samples


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        users.ensure_bootstrap_admin()
    except Exception as e:                       # a bad ADMIN_* value or an unreachable database must not stop the API
        logging.getLogger("marketripple.auth").error("Could not create the admin account: %s", e)
    if settings.live_enabled:
        monitor.start()
    yield
    monitor.shutdown()


app = FastAPI(title="FinPulse AI", version="0.2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# login + admin panel are always reachable; the data routes need a login only when AUTH_REQUIRED=true
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
_gated = [Depends(gate)]
app.include_router(analyze.router, prefix="/api", dependencies=_gated)
app.include_router(samples.router, prefix="/api", dependencies=_gated)
app.include_router(live.router, prefix="/api", dependencies=_gated)
app.include_router(recurrence.router, prefix="/api", dependencies=_gated)
app.include_router(chat.router, prefix="/api", dependencies=_gated)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "FinPulse AI"}
