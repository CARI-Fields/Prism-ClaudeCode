from __future__ import annotations

from contextlib import asynccontextmanager

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from web.api import export, queries
from web.api.auth import require_token
from web.api.config import get_settings
from web.api.data_source import ensure_data, ensure_full_texts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pull the parquet from the private dataset into DATA_DIR (no-op locally).
    s = get_settings()
    ensure_data(s.data_dir, s.hf_dataset_repo, s.hf_token)
    yield


app = FastAPI(title="CC experiment report API", lifespan=lifespan)

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


@app.get("/api/export", dependencies=_GATE)
def export_zip(runs: str = Query(...), texts: int = Query(default=0)) -> Response:
    run_ids = [r for r in runs.split(",") if r]
    if texts:
        try:
            ensure_full_texts()
        except Exception as exc:  # noqa: BLE001 — readable error, not a raw HF stack
            raise HTTPException(
                status_code=503, detail="raw context text is temporarily unavailable"
            ) from exc
    try:
        data = export.build_zip(run_ids, include_texts=bool(texts))
    except ValueError:
        raise HTTPException(status_code=400, detail="no valid run_ids")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cc-traces-{ts}.zip"'},
    )
