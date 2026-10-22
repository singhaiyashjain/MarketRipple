"""FastAPI entrypoint. Run: uvicorn app.main:app --reload   OWNER: M3"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.live.monitor import monitor
from app.routers import analyze, chat, live, recurrence, samples


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.live_enabled:
        monitor.start()
    yield
    monitor.shutdown()


app = FastAPI(title="FinPulse AI", version="0.2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(analyze.router, prefix="/api")
app.include_router(samples.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(recurrence.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "FinPulse AI"}
