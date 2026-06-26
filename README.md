# Claude Code context-window & prefix-cache experiments

Harness that runs Claude Code under five orchestration conditions on a coding
and a research task, captures tracing data (claude-tap + session JSONL), and
feeds the analysis pipeline (Plan B).

## Repository layout

Three pillars — run the experiment, analyse the data, view the report:

    experiment/        # run the experiment, produce raw data
      harness/           runner · capture · conditions · scoring · services
      config/            experiment.yaml · conditions/ · tasks/
      tasks/             task definitions: prompts · seeds · checks
    analysis/          # raw data → tidy tables, figures, reports
      parse/ plots/      pipeline code (importable as `analysis.*`)
      data/              raw/ · processed/   (gitignored — regenerate via `make analyze`)
      figures/           committed plot PNGs
      reports/           report.html · report.md
    web/               # interactive report app
      app/               React/Vite single-page app
      api/               FastAPI + DuckDB read-only API (importable as `web.api`)
    tests/  docs/  scripts/    # shared: pytest suite · specs+plans · deploy/utils

All `make` targets run from the repo root. Python packages: `experiment.harness`,
`analysis`, `web.api`.

## Setup
    make setup        # pip install -e ".[dev]"
    make tap-check    # verify claude-tap is on PATH

## Run one cell
    make run TASK=coding CONDITION=single_agent REP=1

## Run everything (30 runs)
    make run-all

See `docs/superpowers/specs/` for the design and `docs/superpowers/plans/` for plans.
