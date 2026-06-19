from harness.capture.ttft_parse import SseTimer


def test_sse_timer_captures_milestones():
    t = SseTimer()
    t.feed(1.0, "event: message_start")
    t.feed(1.0, 'data: {"type":"message_start"}')
    t.feed(2.0, "event: content_block_start")
    t.feed(3.0, "event: content_block_delta")        # first token
    t.feed(4.0, "event: content_block_delta")        # later token (ignored)
    t.feed(5.0, "event: message_stop")
    assert t.t_message_start == 1.0
    assert t.t_first_text == 3.0
    assert t.t_done == 5.0


def test_timing_row_shape():
    t = SseTimer()
    t.feed(1.5, "event: message_start")
    t.feed(2.5, "event: content_block_delta")
    t.feed(3.5, "event: message_stop")
    row = t.timing_row("req_abc", t_send=1.0, t_done=3.6)
    assert row["request_id"] == "req_abc"
    assert row["ttft_s"] == 2.5 - 1.0
    assert row["prefill_s"] == 1.5 - 1.0
    assert row["total_s"] == 3.6 - 1.0
