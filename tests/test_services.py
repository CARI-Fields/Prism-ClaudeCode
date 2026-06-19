import threading, time
import uvicorn
from harness.services import health


class _S(uvicorn.Server):
    def install_signal_handlers(self): pass


async def ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def test_health_true_when_up_false_when_down():
    cfg = uvicorn.Config(ok_app, host="127.0.0.1", port=8799, log_level="error")
    s = _S(cfg); th = threading.Thread(target=s.run, daemon=True); th.start()
    while not s.started: time.sleep(0.01)
    assert health("http://127.0.0.1:8799") is True
    s.should_exit = True; time.sleep(0.2)
    assert health("http://127.0.0.1:8799") is False
