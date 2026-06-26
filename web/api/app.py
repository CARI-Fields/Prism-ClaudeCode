from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from web.api import queries
from web.api.auth import require_token
from web.api.config import get_settings

app = FastAPI(title="CC experiment report API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

_GATE = [Depends(require_token)]


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/manifest", dependencies=_GATE)
def manifest() -> dict:
    return queries.get_manifest()


@app.get("/api/runs", dependencies=_GATE)
def runs() -> list[dict]:
    return queries.get_runs()


@app.get("/api/turns", dependencies=_GATE)
def turns() -> list[dict]:
    return queries.get_turns()


@app.get("/api/components", dependencies=_GATE)
def components() -> list[dict]:
    return queries.get_components()


@app.get("/api/component-texts", dependencies=_GATE)
def component_texts(
    run_id: str = Query(...), request_index: int | None = Query(default=None)
) -> list[dict]:
    return queries.get_component_texts(run_id, request_index)


@app.get("/api/token-rates", dependencies=_GATE)
def token_rates() -> dict:
    return queries.get_token_rates()
