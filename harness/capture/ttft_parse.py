from __future__ import annotations


class SseTimer:
    """Records SSE milestone wall-clock times from an Anthropic streaming response."""

    def __init__(self) -> None:
        self.t_message_start: float | None = None
        self.t_first_text: float | None = None
        self.t_done: float | None = None

    def feed(self, now: float, raw_line: str) -> None:
        line = raw_line.strip()
        if not line.startswith("event:"):
            return
        event = line[len("event:"):].strip()
        if event == "message_start" and self.t_message_start is None:
            self.t_message_start = now
        elif event == "content_block_delta" and self.t_first_text is None:
            self.t_first_text = now
        elif event == "message_stop":
            self.t_done = now

    def timing_row(self, request_id: str, t_send: float, t_done: float) -> dict:
        def rel(x: float | None) -> float | None:
            return None if x is None else x - t_send
        return {
            "request_id": request_id,
            "t_send_epoch": t_send,
            "prefill_s": rel(self.t_message_start),
            "ttft_s": rel(self.t_first_text),
            "total_s": t_done - t_send,
        }
