import os

from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task

load_dotenv()


def _get_deepseek_llm_name() -> str:
    """
    Return a DeepSeek model name in provider-prefixed format expected by CrewAI/LiteLLM.
    """
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if model.startswith("deepseek/"):
        return model
    return f"deepseek/{model}"


def create_researcher_crew() -> Crew:
    _get_deepseek_llm_name()

    researcher = Agent(
        role="Researcher",
        goal="Research a given topic and gather key facts",
        backstory=(
            "You are a focused research specialist who gathers reliable, "
            "high-signal facts quickly."
        ),
        verbose=True,
    )

    research_task = Task(
        description=(
            "Research the topic: {topic}. "
            "Return concise bullet-point findings with the most important facts."
        ),
        expected_output=(
            "A concise bullet-point list of key research findings for the topic."
        ),
        agent=researcher,
    )

    return Crew(
        agents=[researcher],
        tasks=[research_task],
        process=Process.sequential,
        verbose=True,
    )


def create_analyst_crew() -> Crew:
    _get_deepseek_llm_name()

    analyst = Agent(
        role="Analyst",
        goal="Analyze research findings and produce a short report",
        backstory=(
            "You are an analytical writer who turns raw research notes into "
            "clear insights and practical conclusions."
        ),
        verbose=True,
    )

    analysis_task = Task(
        description=(
            "Analyze these research findings: {research_findings}. "
            "Summarize the core insights and suggest clear conclusions."
        ),
        expected_output=(
            "A short report summarizing insights and recommended conclusions."
        ),
        agent=analyst,
    )

    return Crew(
        agents=[analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True,
    )


researcher_crew = create_researcher_crew()
analyst_crew = create_analyst_crew()

__all__ = [
    "create_researcher_crew",
    "create_analyst_crew",
    "researcher_crew",
    "analyst_crew",
]
