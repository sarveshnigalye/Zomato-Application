# System Evaluation & Benchmark Framework

The comprehensive evaluation framework and benchmark specification for this project is located in:
👉 **[Docs/eval.md](file:///f:/AI%20projects/antigravity/Docs/eval.md)**

Please refer to that file for:
- Core Evaluation KPIs (Retrieval, Grounding, Latency, Fallback)
- 25-Scenario Ground Truth Golden Benchmark Suite
- LLM-as-a-Judge Evaluation Methodology & Rubrics (Faithfulness, Alignment, Persuasiveness, Coherence)
- Automated Evaluation Harness (`backend/tests/eval/run_eval.py`)
- Latency SLA Measurement ($P_{50} < 1.5\text{s}$, $P_{95} < 2.5\text{s}$)
- Release Gating & Quality Gate Thresholds
