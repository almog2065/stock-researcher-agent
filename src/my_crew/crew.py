import os
from datetime import datetime
from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _step_callback(step_output) -> None:
    text = str(step_output)[:120].replace("\n", " ")
    _log(f"  step → {text}…")

@CrewBase
class MyCrew():
    """Stock Researcher Crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @property
    def _llm(self) -> LLM:
        return LLM(
            model=os.environ["OLLAMA_MODEL"],
            base_url=os.environ["OLLAMA_URL"],
            api_key=os.environ["OLLAMA_API_KEY"],
        )

    @agent
    def fundamental_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['fundamental_analyst'],
            llm=self._llm,
            tools=[],
            verbose=True,
        )

    @agent
    def technical_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['technical_analyst'],
            llm=self._llm,
            tools=[],
            verbose=True,
        )

    @agent
    def summary_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['summary_analyst'],
            llm=self._llm,
            tools=[],
            verbose=True,
        )

    @task
    def fundamental_task(self) -> Task:
        return Task(
            config=self.tasks_config['fundamental_task'],
            callback=lambda o: _log("✅ fundamental_task complete"),
        )

    @task
    def technical_task(self) -> Task:
        return Task(
            config=self.tasks_config['technical_task'],
            callback=lambda o: _log("✅ technical_task complete"),
        )

    @task
    def summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['summary_task'],
            callback=lambda o: _log("✅ summary_task complete"),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Stock Researcher crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=_step_callback,
        )
