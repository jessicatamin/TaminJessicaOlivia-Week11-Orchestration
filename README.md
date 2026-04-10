# CrewAI Orchestration Pipeline

This project runs a two-stage CrewAI workflow with checkpoint-based recovery.

## Pipeline Stages

- `stage_0` - **Researcher crew**: researches the given topic and returns bullet-point key facts.
- `stage_1` - **Analyst crew**: consumes previous stage output, summarizes insights, and suggests conclusions.

Each stage is executed sequentially through `run_pipeline(...)` in `pipeline.py`.

## How To Run

1. Ensure `.env` has valid values:
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_MODEL` (for example, `deepseek-chat`)
   - `DEEPSEEK_API_BASE` (for example, `https://api.deepseek.com`)
2. Run:

```bash
python pipeline.py --topic "benefits of renewable energy"
```

You can also run with default empty topic:

```bash
python pipeline.py
```

## Resume After Failure

The pipeline uses `checkpoint.json` to persist completed stages:

- After a stage succeeds, its output is saved as a string under keys like `stage_0`, `stage_1`.
- On rerun, completed stages are auto-detected and skipped.
- The latest completed stage output is passed forward as `previous_result` to the next stage.

No manual resume command is required; rerunning `python pipeline.py` is enough.

## Challenges Encountered

- **`CrewOutput` serialization**: raw crew outputs may not be directly JSON-serializable, so outputs are stored as `str(result)` in checkpoint.
- **Retry behavior**: stage execution can fail due to transient/provider errors; retry logic was implemented with 3 attempts and exponential backoff (`2^attempt` seconds).
- **Version-specific kickoff API**: the installed CrewAI version did not support `kickoff(inputs=...)`, so runtime input injection was handled by formatting task descriptions before kickoff.
- **Resume input propagation**: keeping `previous_result` consistent across skipped and newly executed stages required explicit state tracking.

## Manual Fixes Needed

- A valid DeepSeek API key must be present in `.env`.
- If authentication fails (`401`), regenerate/check key, quota, and account access.
- If provider endpoint/model changes, update:
  - `DEEPSEEK_API_BASE`
  - `DEEPSEEK_MODEL`

`checkpoint.json` is auto-generated; delete it only if you want a full restart from `stage_0`.
