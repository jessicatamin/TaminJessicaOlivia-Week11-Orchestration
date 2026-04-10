import json
import logging
import argparse
import os
import time
from pathlib import Path
from typing import Dict, List

from crewai import Crew
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def _configure_deepseek_runtime_or_raise() -> None:
    """
    Validate required DeepSeek env vars and configure runtime LLM endpoint.

    Note: This project's installed CrewAI version initializes ChatOpenAI by default.
    We map DeepSeek values into runtime variables expected by that client so requests
    are sent to DeepSeek instead of OpenAI.
    """
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip()

    if not api_key or "PASTE_YOUR_DEEPSEEK_API_KEY_HERE" in api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is missing or placeholder. Set a valid key in .env."
        )
    if not api_base:
        raise ValueError("DEEPSEEK_API_BASE is missing. Set it in .env.")

    # Force runtime endpoint/model to DeepSeek to avoid OpenAI regional failures.
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_BASE"] = api_base
    os.environ["OPENAI_BASE_URL"] = api_base
    os.environ["OPENAI_MODEL_NAME"] = model


def _load_checkpoint(checkpoint_path: str) -> Dict[str, str]:
    path = Path(checkpoint_path)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load checkpoint file '%s': %s", checkpoint_path, exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("Checkpoint file '%s' is not a JSON object.", checkpoint_path)
        return {}

    return {str(k): str(v) for k, v in data.items()}


def _save_checkpoint(checkpoint_path: str, state: Dict[str, str]) -> None:
    path = Path(checkpoint_path)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _prepare_crew_inputs(crew: Crew, previous_result: str) -> None:
    """
    Inject runtime values into task descriptions for older CrewAI versions
    where Crew.kickoff() does not accept input arguments.
    """
    for task in getattr(crew, "tasks", []):
        template = getattr(task, "_template_description", None)
        if template is None:
            template = task.description
            setattr(task, "_template_description", template)

        task.description = template.format(
            previous_result=previous_result,
            topic=previous_result,
            research_findings=previous_result,
        )


def run_pipeline(
    crews: List[Crew],
    checkpoint_path: str = "checkpoint.json",
    initial_input: str = "",
) -> Dict[str, str]:
    state: Dict[str, str] = _load_checkpoint(checkpoint_path)

    previous_result = initial_input
    if state:
        latest_stage = max(
            (int(key.split("_")[1]) for key in state.keys() if key.startswith("stage_")),
            default=-1,
        )
        if latest_stage >= 0:
            previous_result = state.get(f"stage_{latest_stage}", "")

    for idx, crew in enumerate(crews):
        stage_name = f"stage_{idx}"

        if stage_name in state:
            logger.info("Skipping %s (already in checkpoint).", stage_name)
            previous_result = state[stage_name]
            continue

        logger.info("Starting %s", stage_name)
        stage_success = False

        for attempt in range(1, 4):
            try:
                _prepare_crew_inputs(crew, previous_result)
                result = crew.kickoff()
                result_str = str(result)
                state[stage_name] = result_str
                _save_checkpoint(checkpoint_path, state)
                previous_result = result_str
                stage_success = True
                logger.info("Completed %s", stage_name)
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Attempt %s failed for %s: %s", attempt, stage_name, exc
                )
                if attempt < 3:
                    backoff_seconds = 2**attempt
                    time.sleep(backoff_seconds)

        if not stage_success:
            logger.error("Failed %s after 3 attempts.", stage_name)
            break

    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sequential CrewAI pipeline.")
    parser.add_argument(
        "--topic",
        default="",
        help="Initial topic input for stage_0 (researcher crew).",
    )
    parser.add_argument(
        "--checkpoint",
        default="checkpoint.json",
        help="Path to checkpoint file.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    _configure_deepseek_runtime_or_raise()

    from crews import analyst_crew, researcher_crew

    crew_sequence = [researcher_crew, analyst_crew]
    final_state = run_pipeline(
        crew_sequence,
        checkpoint_path=args.checkpoint,
        initial_input=args.topic,
    )
    logger.info("Pipeline finished. Final state: %s", final_state)
