# Experiment Report

Runs analyzed: **2**.  (Build-only subset; narrative filled after the full sweep.)

## Runs

| run_id                                     | task   | condition    | success   |   speedup |   num_requests |   total_cache_read |   cache_hit_ratio |   completion_time_s |
|:-------------------------------------------|:-------|:-------------|:----------|----------:|---------------:|-------------------:|------------------:|--------------------:|
| coding__single_agent__01__20260619T210033Z | coding | single_agent | False     |         0 |              7 |             258538 |          0.758292 |             484.984 |
| coding__subagents__01__20260619T212355Z    | coding | subagents    | False     |         0 |            241 |           17366675 |          0.978476 |            4174.53  |


## Prefix-cache-hit accumulation (headline)

![cache](../figures/cache_accumulation.png)

## Context growth by component

![ctx](../figures/context_growth.png)

## Latency (TTFT vs total)

![lat](../figures/latency.png)

## Success rate & speedup

![ss](../figures/success_speedup.png)
