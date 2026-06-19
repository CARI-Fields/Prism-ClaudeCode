import json
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from harness.capture.ttft_proxy import make_app


class _Server(uvicorn.Server):
    def install_signal_handlers(self):  # run in a thread
        pass


def _serve(app, port):
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    srv = _Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    while not srv.started:
        time.sleep(0.01)
    return srv


def test_proxy_records_timing_and_forwards(tmp_path: Path):
    # fake upstream that streams an SSE response with a delay before first token
    async def upstream_app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/event-stream"),
                                (b"request-id", b"req_test123")]})
        chunks = [b"event: message_start\n\n", b"event: content_block_delta\n\n",
                  b"event: message_stop\n\n"]
        for i, c in enumerate(chunks):
            if i == 1:
                time.sleep(0.05)  # simulate prefill latency before first token
            await send({"type": "http.response.body", "body": c, "more_body": i < len(chunks) - 1})

    up = _serve(upstream_app, 8771)
    out = tmp_path / "ttft.jsonl"
    proxy = _serve(make_app(upstream="http://127.0.0.1:8771", out_path=out), 8772)

    r = httpx.post("http://127.0.0.1:8772/v1/messages", json={"x": 1}, timeout=10)
    assert r.status_code == 200
    assert b"message_stop" in r.content  # body forwarded intact
    up.should_exit = True; proxy.should_exit = True
    time.sleep(0.2)

    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["request_id"] == "req_test123"
    assert rows[0]["ttft_s"] >= 0.04  # the injected delay shows up
