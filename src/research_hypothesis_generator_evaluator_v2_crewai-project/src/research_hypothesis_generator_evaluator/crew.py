import os
from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	SerperDevTool
)




@CrewBase
class ResearchHypothesisGeneratorEvaluatorCrew:
    """ResearchHypothesisGeneratorEvaluator crew"""

    
    @agent
    def academic_research_specialist(self) -> Agent:
        
        return Agent(
            config=self.agents_config["academic_research_specialist"],
            tools=[
				SerperDevTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def hypothesis_generator_and_evaluator(self) -> Agent:
        
        return Agent(
            config=self.agents_config["hypothesis_generator_and_evaluator"],
            tools=[
				SerperDevTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    
    @agent
    def debate_analyst_and_critic(self) -> Agent:
        
        return Agent(
            config=self.agents_config["debate_analyst_and_critic"],
            tools=[
				SerperDevTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
        )
    

    
    @task
    def comprehensive_topic_research(self) -> Task:
        return Task(
            config=self.tasks_config["comprehensive_topic_research"],
        )
    
    @task
    def generate_and_evaluate_research_hypotheses(self) -> Task:
        return Task(
            config=self.tasks_config["generate_and_evaluate_research_hypotheses"],
        )
    
    @task
    def debate_analysis_for_each_hypothesis(self) -> Task:
        return Task(
            config=self.tasks_config["debate_analysis_for_each_hypothesis"],
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the ResearchHypothesisGeneratorEvaluator crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
