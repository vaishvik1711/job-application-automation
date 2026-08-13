"""
WebSocket / Socket.IO server for real-time updates.

Provides real-time pipeline progress, job discovery notifications,
matching results, and resume generation status to connected clients.

Usage:
    from api.websocket import sio, emit_pipeline_update
    await emit_pipeline_update("search", 1, 3, "Searching job boards...")
"""
import os
import socketio
from typing import Any, Optional

# CORS origins for Socket.IO — mirror the FastAPI CORS_ORIGINS env var.
_cors_raw = os.getenv("CORS_ORIGINS", "*").split(",")
_sio_origins = "*" if _cors_raw == ["*"] else _cors_raw

# Single AsyncServer instance — reused across the app via get_socketio_app().
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_sio_origins,
    transports=["websocket", "polling"],
)

# Track active connections for diagnostics.
_active_connections: int = 0


@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Handle a new Socket.IO client connection."""
    global _active_connections
    _active_connections += 1
    print(
        f"[Socket.IO] Client connected: {sid} "
        f"(total: {_active_connections})"
    )
    # Let the client know the connection is fully established.
    await sio.emit("ready", {"message": "Connected to real-time server"}, to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    global _active_connections
    _active_connections = max(0, _active_connections - 1)
    print(
        f"[Socket.IO] Client disconnected: {sid} "
        f"(total: {_active_connections})"
    )


@sio.event
async def ping(sid: str, data: Any) -> None:
    """Simple echo-based ping handler for keep-alive / latency checks."""
    await sio.emit("pong", data, to=sid)


# ---------------------------------------------------------------------------
# Helper functions — call these from route handlers or background tasks to
# push real-time events to every connected browser.
# ---------------------------------------------------------------------------

async def emit_pipeline_update(
    stage: str,
    current: int,
    total: int,
    message: str,
    job_id: Optional[str] = None,
) -> None:
    """Broadcast a pipeline_update event to all connected clients."""
    payload: dict[str, Any] = {
        "stage": stage,
        "current": current,
        "total": total,
        "message": message,
    }
    if job_id:
        payload["job_id"] = job_id
    await sio.emit("pipeline_update", payload)


async def emit_job_found(job_data: dict) -> None:
    """Broadcast a job_found event when a new job is discovered."""
    await sio.emit("job_found", job_data)


async def emit_match_complete(match_data: dict) -> None:
    """Broadcast a match_complete event when job matching finishes."""
    await sio.emit("match_complete", match_data)


async def emit_resume_generated(resume_data: dict) -> None:
    """Broadcast a resume_generated event when a resume is created."""
    await sio.emit("resume_generated", resume_data)


async def emit_progress(
    stage: str,
    current: int,
    total: int,
    message: str,
    job_id: Optional[str] = None,
) -> None:
    """Broadcast a progress event to all connected clients."""
    payload: dict[str, Any] = {
        "stage": stage,
        "current": current,
        "total": total,
        "message": message,
    }
    if job_id:
        payload["job_id"] = job_id
    await sio.emit("progress", payload)


async def emit_error(message: str, code: str = "websocket_error") -> None:
    """Broadcast an error event to all connected clients."""
    await sio.emit("error", {"message": message, "code": code})


def get_socketio_app(asgi_app: Any) -> socketio.ASGIApp:
    """
    Wrap an existing ASGI app (e.g. FastAPI) with the Socket.IO middleware.

    The returned object is itself an ASGI application suitable for passing
    to ``uvicorn``.
    """
    return socketio.ASGIApp(sio, other_asgi_app=asgi_app)
