"""FastAPI application: JSON API under /api, and the built React app on every other path."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import date, time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, settings
from .repository import Repository
from .schemas import Accuracy, DayAhead, Meta
from .service import WindService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


def service_dep(request: Request) -> WindService:
    try:
        return request.app.state.get_service()
    except Exception as exc:
        log.exception("Data unavailable")
        raise HTTPException(503, "Wind data is not available yet, please retry.") from exc


Svc = Annotated[WindService, Depends(service_dep)]


def create_app(app_settings: Settings = settings, repository: Repository | None = None) -> FastAPI:
    repo = repository or Repository(app_settings)
    service_lock = threading.Lock()
    service_holder: dict[str, WindService] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Warm the dataset in the background so the first user request is fast.
        threading.Thread(target=_warm, daemon=True).start()
        yield

    def _warm() -> None:
        try:
            get_service()
        except Exception:  # surfaced to clients as 503 on request
            log.exception("Initial data load failed")

    def get_service() -> WindService:
        with service_lock:
            if "svc" not in service_holder:
                service_holder["svc"] = WindService(app_settings, repo.get())
            return service_holder["svc"]

    app = FastAPI(title="Wind Forecast Monitor API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
    app.state.get_service = get_service

    def parse_decision_time(svc: WindService, value: str | None) -> time:
        if value is None:
            return svc.settings.default_decision_time
        try:
            return time.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(422, "decision_time must be HH:MM") from exc

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "dataLoaded": repo.loaded}

    @app.get("/api/meta", response_model=Meta)
    def meta(svc: Svc) -> Meta:
        return svc.meta()

    @app.get("/api/day-ahead", response_model=DayAhead)
    def day_ahead(
        svc: Svc,
        delivery_date: Annotated[date, Query(description="UK delivery day D")],
        decision_time: Annotated[
            str | None, Query(description="UK local time on D-1, HH:MM")
        ] = None,
    ) -> DayAhead:
        w = svc.window
        if not w.delivery_from <= delivery_date <= w.delivery_to:
            raise HTTPException(
                422, f"delivery_date must be between {w.delivery_from} and {w.delivery_to}"
            )
        return svc.day_ahead(delivery_date, parse_decision_time(svc, decision_time))

    @app.get("/api/accuracy", response_model=Accuracy)
    def accuracy(
        svc: Svc,
        decision_time: Annotated[
            str | None, Query(description="UK local time on D-1, HH:MM")
        ] = None,
    ) -> Accuracy:
        return svc.accuracy(parse_decision_time(svc, decision_time))

    _mount_frontend(app, app_settings)
    return app


def _mount_frontend(app: FastAPI, app_settings: Settings) -> None:
    static = app_settings.static_dir
    index = static / "index.html"
    if not index.exists():
        return
    if (static / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
