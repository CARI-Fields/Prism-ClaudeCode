from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route

from experiment.harness.capture.ttft_parse import SseTimer


def make_app(upstream: str, out_path: Path) -> Starlette:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    client = httpx.AsyncClient(base_url=upstream, timeout=httpx.Timeout(600.0))

    async def handler(request):
        body = await request.body()
        fwd_headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in ("host", "content-length")}
        t_send = time.time()
        timer = SseTimer()
        req = client.build_request(request.method, request.url.path,
                                   params=request.url.query, headers=fwd_headers, content=body)
        upstream_resp = await client.send(req, stream=True)
        request_id = upstream_resp.headers.get("request-id", "")

        async def stream():
            buf = ""
            try:
                async for chunk in upstream_resp.aiter_raw():
                    now = time.time()
                    try:
                        buf += chunk.decode("utf-8", "replace")
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            timer.feed(now, line)
                    except Exception:
                        pass
                    yield chunk
                t_done = time.time()
                row = timer.timing_row(request_id, t_send, t_done)
                row["status"] = upstream_resp.status_code
                with out_path.open("a") as f:
                    f.write(json.dumps(row) + "\n")
            finally:
                await upstream_resp.aclose()

        resp_headers = {k: v for k, v in upstream_resp.headers.items()
                        if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")}
        return StreamingResponse(stream(), status_code=upstream_resp.status_code,
                                 headers=resp_headers)

    return Starlette(routes=[Route("/{path:path}", handler, methods=["POST", "GET"])])


def main(argv: list[str] | None = None) -> int:
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--upstream", default="https://api.anthropic.com")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    uvicorn.run(make_app(args.upstream, Path(args.out)), host="127.0.0.1", port=args.port,
                log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
