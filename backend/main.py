"""Red Planet Mission Control — FastAPI backend."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from backend.telemetry import TelemetryStats

app = FastAPI(title="Red Planet Mission Control", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")


class ReadingsRequest(BaseModel):
    readings: list[float]


@app.get("/")
def index():
    return FileResponse(str(_FRONTEND / "index.html"))


@app.get("/api/health")
def health():
    """Liveness check."""
    return {"status": "ok", "mission": "Red Planet"}


@app.post("/api/stats")
def compute_stats(req: ReadingsRequest):
    """Compute descriptive statistics over telemetry readings."""
    if not req.readings:
        raise HTTPException(status_code=422, detail="readings must not be empty")
    stats = TelemetryStats(req.readings)
    return stats.summary()
