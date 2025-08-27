import os
from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	ScrapeWebsiteTool
)




@CrewBase
class ResearchAssistantHypothesisDiscoveryPaperWritingCrew:
    """ResearchAssistantHypothesisDiscoveryPaperWriting crew"""

    
    @agent
    def latex_formatter_journal_specialist(self) -> Agent:
        
        return Agent(
            config=self.agents_config["latex_formatter_journal_specialist"],
            tools=[

            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def related_work_specialist(self) -> Agent:
        
        return Agent(
            config=self.agents_config["related_work_specialist"],
            tools=[
				ScrapeWebsiteTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def methodology_expert(self) -> Agent:
        
        return Agent(
            config=self.agents_config["methodology_expert"],
            tools=[

            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def results_analysis_specialist(self) -> Agent:
        
        return Agent(
            config=self.agents_config["results_analysis_specialist"],
            tools=[

            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def discussion_conclusion_expert(self) -> Agent:
        
        return Agent(
            config=self.agents_config["discussion_conclusion_expert"],
            tools=[

            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def research_explorer_hypothesis_generator(self) -> Agent:
        
        return Agent(
            config=self.agents_config["research_explorer_hypothesis_generator"],
            tools=[
				ScrapeWebsiteTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    

    
    @task
    def research_discovery_hypothesis_exploration(self) -> Task:
        return Task(
            config=self.tasks_config["research_discovery_hypothesis_exploration"],
        )
    
    @task
    def related_work_analysis_synthesis(self) -> Task:
        return Task(
            config=self.tasks_config["related_work_analysis_synthesis"],
        )
    
    @task
    def methodology_design(self) -> Task:
        return Task(
            config=self.tasks_config["methodology_design"],
        )
    
    @task
    def results_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["results_analysis"],
        )
    
    @task
    def discussion_conclusions(self) -> Task:
        return Task(
            config=self.tasks_config["discussion_conclusions"],
        )
    
    @task
    def latex_paper_assembly(self) -> Task:
        return Task(
            config=self.tasks_config["latex_paper_assembly"],
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the ResearchAssistantHypothesisDiscoveryPaperWriting crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
