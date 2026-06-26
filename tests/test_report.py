import math
import shutil
from pathlib import Path
import pandas as pd
from analysis.echarts_report import build_dashboard_data, render_echarts_report
from analysis.report import generate


def _make_run(tmp):
    d = tmp / "data/raw/coding__single_agent__01__20260619T210033Z"
    (d / "tap").mkdir(parents=True); (d / "ttft").mkdir(); (d / "transcripts").mkdir()
    shutil.copy("tests/fixtures/real_cell/tap.json", d / "tap/s.json")
    shutil.copy("tests/fixtures/real_cell/ttft.jsonl", d / "ttft/ttft.jsonl")
    shutil.copy("tests/fixtures/real_cell/run_meta.json", d / "run_meta.json")


def test_generate_report(tmp_path):
    _make_run(tmp_path)
    rep = generate(tmp_path / "data/raw", tmp_path / "processed",
                   tmp_path / "figures", tmp_path / "report.md")
    text = Path(rep).read_text()
    assert "Prefix-cache" in text or "cache_accumulation" in text
    assert "| condition |" in text or "condition" in text
    assert (tmp_path / "figures" / "cache_accumulation.png").exists()
    assert "Condition overhead vs single-agent baseline" in text

    # report.html is now ONE single-page report with a masthead switcher; report.md
    # deep-links each read into it.
    assert '<iframe src="report.html#report=multi_agent"' in text
    assert '<iframe src="report.html#report=long_horizon"' in text
    assert "(report.html)" in text

    page = (tmp_path / "report.html").read_text()
    assert "https://cdn.jsdelivr.net/npm/echarts" in page
    assert "echarts.init" in page
    # the chart code lives ONCE; both reports' data ride in separate JSON blocks.
    for chart_id in (
        "matrix-chart", "condition-chart", "overhead-chart", "efficiency-chart",
        "cache-chart", "latency-chart", "run-chart", "component-chart",
    ):
        assert chart_id in page
    # the switcher offers both reads, with the shared chart shell
    assert 'class="switch-tab" data-report="multi_agent"' in page
    assert 'class="switch-tab" data-report="long_horizon"' in page
    assert 'id="reports-manifest"' in page
    assert 'id="rpt-multi_agent-data"' in page
    assert 'id="rpt-long_horizon-data"' in page
    assert "activateReport" in page
    # each report's data is scoped to exactly its strategies
    assert '"conditions":["single_agent","subagents","dynamic_workflow"]' in page
    assert '"conditions":["goal","ralph_loop","dynamic_workflow"]' in page
    # §0 task-prompt band content for both reads is embedded in the manifest
    assert "Tasks &amp; strategies" in page
    assert "Fused Triton kernel" in page               # multi-agent task title
    assert "Kernel gauntlet" in page                   # long-horizon task title
    assert "Strategies compared" in page
    # long-horizon is scaffolded around its (data-less) long-horizon tasks
    assert '"tasks":["coding_longhorizon","research_longhorizon"]' in page


def test_subreport_scopes_conditions_and_adds_task_brief(tmp_path):
    from analysis.report_variants import VARIANTS, build_page

    runs = pd.DataFrame([
        {"run_id": "coding__single_agent__01", "task": "coding",
         "condition": "single_agent", "rep": 1, "success": True},
        {"run_id": "coding__goal__01", "task": "coding",
         "condition": "goal", "rep": 1, "success": True},
    ])
    multi = next(v for v in VARIANTS if v["key"] == "multi_agent")
    page = build_page(multi, runs)
    out = render_echarts_report(
        runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "ma.html",
        conditions=multi["conditions"], tasks=multi["tasks"], page=page,
    )
    s = out.read_text()
    # goal is dropped from the comparison entirely (single/subagents/dynamic only)
    assert '"conditions":["single_agent","subagents","dynamic_workflow"]' in s
    assert '"condition":"goal"' not in s   # no goal run data embedded
    # §0 band present, masthead gradient encodes the three compared conditions
    assert "band-brief" in s and "Tasks &amp; strategies" in s
    assert "linear-gradient(90deg, #3b5bdb" in s


def test_default_report_has_no_task_brief_band(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    s = render_echarts_report(runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "r.html").read_text()
    # the combined-report default keeps its original layout and resolves every placeholder
    assert '<section class="band band-brief">' not in s   # no §0 band rendered
    assert "Tasks &amp; strategies" not in s
    assert "__BRIEF_BAND__" not in s
    assert "__MASTHEAD_GRADIENT__" not in s


def test_echarts_dashboard_data_includes_single_agent_overheads():
    runs = pd.DataFrame([
        {
            "run_id": "research__single_agent__01",
            "task": "research",
            "condition": "single_agent",
            "rep": 1,
            "success": True,
            "completion_time_s": 10.0,
            "num_requests": 2,
            "cache_hit_ratio": 0.25,
            "total_cache_read": 100,
            "peak_prompt_tokens": 1000,
            "output_tokens_total": 200,
            "total_cost_usd": 0.10,
            "quality_score": 80.0,
            "cost_efficiency_score": 800.0,
        },
        {
            "run_id": "research__loop_dynamic__01",
            "task": "research",
            "condition": "loop_dynamic",
            "rep": 1,
            "success": True,
            "completion_time_s": 40.0,
            "num_requests": 8,
            "cache_hit_ratio": 0.75,
            "total_cache_read": 600,
            "peak_prompt_tokens": 3000,
            "output_tokens_total": 500,
            "total_cost_usd": 0.40,
            "quality_score": 90.0,
            "cost_efficiency_score": 225.0,
        },
    ])
    turns = pd.DataFrame()
    components = pd.DataFrame()

    data = build_dashboard_data(runs, turns, components)

    assert "condition_overheads" in data
    loop = next(
        row for row in data["condition_overheads"]
        if row["task"] == "research" and row["condition"] == "loop_dynamic"
    )
    assert loop["num_requests_factor"] == 4.0
    assert loop["completion_time_factor"] == 4.0
    assert loop["peak_prompt_tokens_factor"] == 3.0
    assert loop["total_cache_read_factor"] == 6.0
    assert loop["total_cost_factor"] == 4.0


def test_echarts_dashboard_includes_goal_condition():
    data = build_dashboard_data(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    assert "goal" in data["conditions"]
    assert any(cell["condition"] == "goal" for cell in data["matrix"])


def test_echarts_dashboard_data_includes_accumulated_cache_hit_rate():
    runs = pd.DataFrame([{
        "run_id": "coding__loop_dynamic__01",
        "task": "coding",
        "condition": "loop_dynamic",
        "rep": 1,
        "success": True,
    }])
    turns = pd.DataFrame([
        {
            "run_id": "coding__loop_dynamic__01",
            "task": "coding",
            "condition": "loop_dynamic",
            "rep": 1,
            "request_index": 0,
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read": 0,
            "cache_creation_5m": 0,
            "cache_creation_1h": 100,
            "request_type": "main-agent",
        },
        {
            "run_id": "coding__loop_dynamic__01",
            "task": "coding",
            "condition": "loop_dynamic",
            "rep": 1,
            "request_index": 1,
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read": 90,
            "cache_creation_5m": 20,
            "cache_creation_1h": 0,
            "request_type": "main-agent",
        },
    ])

    data = build_dashboard_data(runs, turns, pd.DataFrame())
    rows = data["cache_timeline"]

    assert rows[0]["accumulated_cache_hit_rate"] == 0
    assert math.isclose(rows[1]["accumulated_cache_hit_rate"], 90 / (90 + 120 + 20))
    assert rows[1]["cum_total_context_tokens"] == 230
    assert rows[1]["request_type"] == "main-agent"


def test_echarts_cache_timeline_counts_warm_cache_as_observed():
    runs = pd.DataFrame([{
        "run_id": "coding__dynamic_workflow__01",
        "task": "coding",
        "condition": "dynamic_workflow",
        "rep": 1,
        "success": True,
    }])
    turns = pd.DataFrame([
        {
            "run_id": "coding__dynamic_workflow__01",
            "task": "coding",
            "condition": "dynamic_workflow",
            "rep": 1,
            "request_index": 0,
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read": 100,
            "cache_creation_5m": 50,
            "cache_creation_1h": 0,
            "request_type": "main-agent",
        },
        {
            "run_id": "coding__dynamic_workflow__01",
            "task": "coding",
            "condition": "dynamic_workflow",
            "rep": 1,
            "request_index": 1,
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read": 150,
            "cache_creation_5m": 10,
            "cache_creation_1h": 0,
            "request_type": "main-agent",
        },
        {
            "run_id": "coding__dynamic_workflow__01",
            "task": "coding",
            "condition": "dynamic_workflow",
            "rep": 1,
            "request_index": 2,
            "input_tokens": 5,
            "output_tokens": 1,
            "cache_read": 20,
            "cache_creation_5m": 30,
            "cache_creation_1h": 0,
            "request_type": "workflow-subagent",
        },
    ])

    data = build_dashboard_data(runs, turns, pd.DataFrame())
    rows = data["cache_timeline"]

    # No warm-start subtraction: every reported cache read is counted as-observed.
    assert rows[0]["accumulated_cache_hit_rate"] == 100 / 160
    assert rows[0]["cum_cache_read"] == 100
    assert math.isclose(rows[1]["accumulated_cache_hit_rate"], 250 / 330)
    assert rows[2]["cum_cache_read"] == 270
    assert math.isclose(rows[2]["accumulated_cache_hit_rate"], 270 / 385)


def test_echarts_dashboard_data_includes_fine_grained_context_token_components():
    runs = pd.DataFrame([{
        "run_id": "coding__subagents__01",
        "task": "coding",
        "condition": "subagents",
        "rep": 1,
        "success": True,
    }])
    turns = pd.DataFrame([{
        "run_id": "coding__subagents__01",
        "task": "coding",
        "condition": "subagents",
        "rep": 1,
        "request_index": 0,
        "input_tokens": 11,
            "output_tokens": 7,
            "cache_read": 13,
            "cache_creation_5m": 17,
            "cache_creation_1h": 19,
            "request_type": "task-subagent",
        }])

    data = build_dashboard_data(runs, turns, pd.DataFrame())
    rows = data["context_token_components"]
    values = {(row["request_index"], row["component"]): row["tokens"] for row in rows}

    assert values[(0, "input tokens")] == 11
    assert values[(0, "prefix cache read")] == 13
    assert values[(0, "prefix cache write 5m")] == 17
    assert values[(0, "prefix cache write 1h")] == 19
    assert values[(0, "output tokens")] == 7
    assert {row["request_type"] for row in rows} == {"task-subagent"}


def test_echarts_dashboard_data_includes_context_source_components():
    runs = pd.DataFrame([{
        "run_id": "coding__subagents__01",
        "task": "coding",
        "condition": "subagents",
        "rep": 1,
        "success": True,
    }])
    components = pd.DataFrame([
        {
            "run_id": "coding__subagents__01",
            "task": "coding",
            "condition": "subagents",
            "rep": 1,
            "request_index": 0,
            "component": "base system prompt",
            "est_tokens": 10,
            "bytes": 40,
            "request_type": "main-agent",
        },
        {
            "run_id": "coding__subagents__01",
            "task": "coding",
            "condition": "subagents",
            "rep": 1,
            "request_index": 0,
            "component": "CLAUDE.md / project instructions",
            "est_tokens": 20,
            "bytes": 80,
            "request_type": "main-agent",
        },
        {
            "run_id": "coding__subagents__01",
            "task": "coding",
            "condition": "subagents",
            "rep": 1,
            "request_index": 0,
            "component": "MCP / extension tool definitions",
            "est_tokens": 7,
            "bytes": 28,
            "request_type": "web-search-subagent",
        },
    ])

    data = build_dashboard_data(runs, pd.DataFrame(), components)
    rows = data["context_source_components"]
    values = {(row["request_index"], row["component"]): row["est_tokens"] for row in rows}

    assert values[(0, "base system prompt")] == 10
    assert values[(0, "CLAUDE.md / project instructions")] == 20
    assert values[(0, "MCP / extension tool definitions")] == 7
    assert "web-search-subagent" in {row["request_type"] for row in rows}


def test_echarts_report_uses_clear_request_timeline_and_context_labels(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01",
        "task": "coding",
        "condition": "single_agent",
        "rep": 1,
        "success": True,
    }])
    turns = pd.DataFrame([{
        "run_id": "coding__single_agent__01",
        "task": "coding",
        "condition": "single_agent",
        "rep": 1,
        "request_index": 0,
        "input_tokens": 11,
        "output_tokens": 7,
        "cache_read": 13,
        "cache_creation_5m": 17,
        "cache_creation_1h": 19,
        "ttft_s": 1.5,
        "total_s": 3.0,
        "request_type": "web-fetch-subagent",
    }])

    out = render_echarts_report(runs, turns, pd.DataFrame(), tmp_path / "report.html")
    page = out.read_text()

    assert "Prefix Cache Hit Rate (accumulated)" in page
    assert "Per-Run Request Cost Timeline" in page
    assert "Mean total cost ($)" in page
    assert "Quality vs cost map" in page
    assert "Total cost" in page
    assert "Request # within selected run" in page
    assert 'xAxis: { type: "value", name: "Request # within selected run", min: 1 }' in page
    assert "Context Source Breakdown" in page
    assert "CLAUDE.md / project instructions" in page
    assert "MCP / extension tool definitions" in page
    assert "Request type" in page
    assert "main-agent" in page
    assert "security-monitor" in page
    assert "workflow-subagent" in page
    assert "task-subagent" in page
    assert "web-search-subagent" in page
    assert "web-fetch-subagent" in page
    assert "requestTypeSymbols" in page


def test_context_breakdown_has_compose_and_group_controls(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    page = render_echarts_report(runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "report.html").read_text()
    # two per-panel selects: compose (source/token type) and group (agent type/none)
    assert 'id="compose-filter"' in page
    assert 'id="group-filter"' in page
    assert ">token type<" in page and ">agent type<" in page
    # the previously-unused token-bucket dataset is now wired into the renderer
    assert "context_token_components" in page
    assert "renderStackedContextChart" in page
    # agent-type region bands + the clarified ordering note
    assert "markArea" in page
    assert "canonical context order" in page
    # token mode excludes output and folds cache writes into one bucket
    assert '"cache write"' in page
    # the variable-series guard is still present on this chart
    assert "{ notMerge: true }" in page


def test_variable_series_charts_replace_instead_of_merge(tmp_path):
    # The cache-chart and component-chart have a series count that changes with the
    # task/run filter. ECharts setOption merges series by index by default, so when
    # the count shrinks (e.g. All -> Research) stale "ghost" series from the previous
    # selection persist and the axis tooltip shows every run twice. They must render
    # with {notMerge: true} so the series array is replaced, not merged.
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    out = render_echarts_report(runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "report.html")
    page = out.read_text()
    assert page.count("{ notMerge: true }") >= 2


def test_dashboard_data_includes_per_agent_type_cache():
    runs = pd.DataFrame([{
        "run_id": "research__loop_dynamic__01", "task": "research",
        "condition": "loop_dynamic", "rep": 1, "success": True,
    }])
    turns = pd.DataFrame([
        {"run_id": "research__loop_dynamic__01", "task": "research", "condition": "loop_dynamic",
         "rep": 1, "request_index": 0, "input_tokens": 10, "output_tokens": 1, "cache_read": 0,
         "cache_creation_5m": 100, "cache_creation_1h": 0, "request_type": "main-agent"},
        {"run_id": "research__loop_dynamic__01", "task": "research", "condition": "loop_dynamic",
         "rep": 1, "request_index": 1, "input_tokens": 10, "output_tokens": 1, "cache_read": 90,
         "cache_creation_5m": 10, "cache_creation_1h": 0, "request_type": "main-agent"},
        {"run_id": "research__loop_dynamic__01", "task": "research", "condition": "loop_dynamic",
         "rep": 1, "request_index": 2, "input_tokens": 5, "output_tokens": 1, "cache_read": 20,
         "cache_creation_5m": 5, "cache_creation_1h": 0, "request_type": "workflow-subagent"},
    ])
    data = build_dashboard_data(runs, turns, pd.DataFrame())
    rows = data["cache_by_agent"]
    # one independent stream per (run, request_type), each with its own ordinal 1..n
    main = [r for r in rows if r["request_type"] == "main-agent"]
    wf = [r for r in rows if r["request_type"] == "workflow-subagent"]
    assert [r["ordinal"] for r in main] == [1, 2]
    assert [r["ordinal"] for r in wf] == [1]
    assert main[0]["accumulated_cache_hit_rate"] == 0  # warm-start stripped on first request
    assert wf[0]["ordinal"] == 1


def test_report_exposes_agent_type_and_hitrate_controls(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    page = render_echarts_report(runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "report.html").read_text()
    # filters live in the left sidebar as multi-select chip groups
    assert 'id="chips-agent"' in page                  # agent-type multi-select group
    assert 'id="chips-condition"' in page              # condition multi-select group
    assert 'id="sidebar"' in page                      # sticky left filter rail
    assert "cache_by_agent" in page
    assert "context length (tokens)" in page           # scatter x axis
    assert "prefix cache hit rate (%)" in page         # scatter y axis
    assert 'id="reports-manifest"' in page             # report manifest present
    assert 'id="rpt-report-texts"' in page             # per-report context-text block


def test_context_text_panel_embeds_provided_text(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    component_texts = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding", "condition": "single_agent",
        "rep": 1, "request_index": 0, "component": "CLAUDE.md / project instructions",
        "request_type": "main-agent", "text": "UNIQUE_CLAUDE_MD_PREVIEW_TEXT",
        "truncated": False, "bytes": 29, "stable": True,
    }])
    page = render_echarts_report(
        runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "report.html", component_texts
    ).read_text()
    assert "UNIQUE_CLAUDE_MD_PREVIEW_TEXT" in page
    assert "coding__single_agent__01|*|CLAUDE.md / project instructions" in page
    assert "showContextText" in page


def test_tap_component_texts_marks_stable_and_volatile():
    from analysis.parse.parse_tap import tap_component_texts
    tap = [
        {"system": [{"type": "text", "text": "FIXED SYSTEM PROMPT"}],
         "messages": [{"role": "user", "content": [{"type": "text", "text": "first question"}]}],
         "response": {"usage": {"input_tokens": 1}}},
        {"system": [{"type": "text", "text": "FIXED SYSTEM PROMPT"}],
         "messages": [{"role": "user", "content": [{"type": "text", "text": "second question"}]}],
         "response": {"usage": {"input_tokens": 1}}},
    ]
    rows = tap_component_texts(tap)
    sys_rows = [r for r in rows if r["component"] == "base system prompt"]
    user_rows = [r for r in rows if r["component"] == "user input"]
    # identical across turns -> emitted once, stable
    assert len(sys_rows) == 1 and sys_rows[0]["stable"] is True
    # varies per turn -> emitted per request, not stable
    assert len(user_rows) == 2 and all(r["stable"] is False for r in user_rows)
    assert {r["text"] for r in user_rows} == {"first question", "second question"}


def test_recompute_est_tokens_density_weighted_keeps_totals_exact():
    from analysis.build_tables import _recompute_est_tokens
    # 14 requests, two categories with different real densities (A denser than B).
    # The provided est_tokens are uniform byte-proportional (what tap_components emits).
    rows = []
    for i in range(14):
        a_bytes, b_bytes = 1000 + i, 1000 + 100 * i
        total = round(a_bytes * 0.4 + b_bytes * 0.2)
        s = a_bytes + b_bytes
        ea = round(a_bytes / s * total)
        rows += [
            {"run_id": "r", "request_index": i, "component": "A", "bytes": a_bytes, "est_tokens": ea},
            {"run_id": "r", "request_index": i, "component": "B", "bytes": b_bytes, "est_tokens": total - ea},
        ]
    df = pd.DataFrame(rows)
    out, coef = _recompute_est_tokens(df)
    assert coef and coef["A"] > coef["B"]          # recovered: A is denser per byte
    # per-request totals stay EXACTLY the same (still anchored to the measured total)
    new = out.groupby(["run_id", "request_index"])["est_tokens"].sum()
    old = df.groupby(["run_id", "request_index"])["est_tokens"].sum()
    assert (new == old).all()
    # the split shifted toward A (denser) vs the uniform byte-proportional split
    a_new = out[(out["request_index"] == 13) & (out["component"] == "A")]["est_tokens"].iloc[0]
    a_old = df[(df["request_index"] == 13) & (df["component"] == "A")]["est_tokens"].iloc[0]
    assert a_new > a_old


def test_drilldown_charts_grouped_axis_and_context_length(tmp_path):
    runs = pd.DataFrame([{
        "run_id": "coding__single_agent__01", "task": "coding",
        "condition": "single_agent", "rep": 1, "success": True,
    }])
    page = render_echarts_report(runs, pd.DataFrame(), pd.DataFrame(), tmp_path / "r.html").read_text()
    # shared §3 grouping helpers + second agent-type axis + fixed context-length range
    for s in ("function orderedRequests", "function groupedXAxis", "contextLengthMax",
              "runTokenMax", '"context length (tokens)"'):
        assert s in page, s
    # the run chart now reads the shared group toggle (same as the component chart)
    assert page.count('group-filter") || {}).value') >= 2
    # KPIs on one row; baseline tag on its own line
    assert "grid-template-columns:repeat(5" in page
    assert ".strat-line" in page
    # honest note: total exact, split data-calibrated, count_tokens as the exact path
    assert "data-calibrated estimate" in page and "count_tokens API" in page
