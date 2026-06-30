Write a thorough, well-cited technical report to `report.md`: a **comparative
deep-dive on production LLM inference-serving systems**. This is a long-horizon
research task — it is expected to take many turns of real multi-source research,
not a single pass. Do the research properly; do not cite from memory.

Cover these eight systems, one `##` section each, in this order:

1. `## vLLM`
2. `## TensorRT-LLM`
3. `## SGLang`
4. `## TGI`
5. `## LMDeploy`
6. `## DeepSpeed-MII`
7. `## llama.cpp`
8. `## MLC-LLM`

For **every** system section, research and report on all of:
- **Scheduling / batching** (e.g. continuous / in-flight batching, chunked prefill)
- **KV-cache management** (e.g. PagedAttention, RadixAttention / prefix caching, eviction, offload)
- **Quantization support** (weight/activation/KV: e.g. AWQ, GPTQ, FP8, INT4)
- **Parallelism / disaggregation** (tensor/pipeline parallel, prefill-decode disaggregation, speculative decoding)
- **Notable measured performance claims**, with the source

Then add two synthesis sections:

9. `## Comparison Matrix` — a Markdown table with one row per system and columns for
   the five dimensions above (a short cell each).
10. `## Tradeoffs & Recommendations` — when to pick which system, grounded in the
    evidence above (latency-bound vs throughput-bound serving, long-context,
    quantization needs, hardware, multi-GPU).

Research method (this is the long-horizon part — iterate):
- Actually search and fetch primary sources: official docs, design blogs, papers,
  and benchmarks for each system. Read them; do not summarize from memory.
- Cross-check claims across sources where they disagree.
- Build the report incrementally: write `report.md` early and keep expanding and
  revising it as you research each system, then fill the matrix and synthesis last.

Completion criteria — finish only when `report.md` satisfies ALL of:
- all ten `##` section headings above are present, in order;
- each of the eight system sections names its KV-cache mechanism, its
  batching/scheduling approach, and at least one quantization format;
- at least **30 distinct** `http`/`https` source URLs total;
- length **3000–4500 words**;
- the Comparison Matrix has a row for all eight systems.

Before finishing, re-read `report.md` and verify every criterion above is met.
