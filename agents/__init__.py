"""Agent registry — all 13 product builder agents."""
from agents.prd_parser_agent import PRDParserAgent
from agents.architect_agent import ArchitectAgent
from agents.database_agent import DatabaseAgent
from agents.api_designer_agent import APIDesignerAgent
from agents.planner_agent import PlannerAgent
from agents.coder_agent import CoderAgent
from agents.reviewer_agent import ReviewerAgent
from agents.qa_agent import QAAgent
from agents.frontend_agent import FrontendAgent
from agents.integration_agent import IntegrationAgent
from agents.devops_agent import DevOpsAgent
from agents.docs_agent import DocsAgent
from agents.github_agent import GitHubAgent

__all__ = [
    "PRDParserAgent",
    "ArchitectAgent",
    "DatabaseAgent",
    "APIDesignerAgent",
    "PlannerAgent",
    "CoderAgent",
    "ReviewerAgent",
    "QAAgent",
    "FrontendAgent",
    "IntegrationAgent",
    "DevOpsAgent",
    "DocsAgent",
    "GitHubAgent",
]
