# Claude Code context-window & prefix-cache experiments

Harness that runs Claude Code under five orchestration conditions on a coding
and a research task, captures tracing data (claude-tap + session JSONL), and
feeds the analysis pipeline (Plan B).

## Setup
    make setup        # pip install -e ".[dev]"
    make tap-check    # verify claude-tap is on PATH

## Run one cell
    make run TASK=coding CONDITION=single_agent REP=1

## Run everything (30 runs)
    make run-all

See `docs/superpowers/specs/` for the design and `docs/superpowers/plans/` for plans.
