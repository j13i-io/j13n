from typing import Optional, Dict, Any
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from bs4 import BeautifulSoup
import requests
from ..models.job_models import JobResult
from ..config.settings import get_settings

class JobApplicationService:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4-turbo-preview",
            openai_api_key=self.settings.OPENAI_API_KEY
        )
        self._setup_chains()

    def _setup_chains(self):
        # Chain for analyzing job requirements
        analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert job application analyzer. Analyze the job description and requirements."),
            ("user", "Job Title: {job_title}\nCompany: {company}\nDescription: {description}\nSnippet: {snippet}\n\nAnalyze the key requirements and qualifications needed for this position.")
        ])
        self.analyze_chain = LLMChain(llm=self.llm, prompt=analyze_prompt)

        # Chain for generating application content
        apply_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert job application writer. Generate a tailored application based on the job requirements."),
            ("user", "Job Title: {job_title}\nCompany: {company}\nLocation: {location}\nRequirements Analysis: {requirements_analysis}\n\nGenerate a tailored cover letter and resume highlights for this position.")
        ])
        self.apply_chain = LLMChain(llm=self.llm, prompt=apply_prompt)

    async def scrape_job_details(self, job_url: str) -> Dict[str, Any]:
        """Scrape job details from the provided URL"""
        try:
            response = requests.get(job_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Basic extraction - this should be customized based on the job board structure
            title = soup.find('h1').text.strip() if soup.find('h1') else ""
            description = soup.find('div', class_='job-description').text.strip() if soup.find('div', class_='job-description') else ""

            return {
                "title": title,
                "description": description
            }
        except Exception as e:
            raise Exception(f"Error scraping job details: {str(e)}")

    async def analyze_job(self, job: JobResult) -> Dict[str, Any]:
        """Analyze job requirements using LangChain"""
        try:
            # Scrape job details
            job_details = await self.scrape_job_details(job.link)

            # Use the job title from search results if scraping didn't find one
            job_title = job_details["title"] or job.title

            # Analyze requirements
            analysis = await self.analyze_chain.arun(
                job_title=job_title,
                company=job.company,
                description=job_details["description"],
                snippet=job.snippet
            )

            return {
                "job_details": {
                    **job_details,
                    "title": job_title,
                    "company": job.company,
                    "location": job.location,
                    "posted_date": job.posted_date
                },
                "requirements_analysis": analysis
            }
        except Exception as e:
            raise Exception(f"Error analyzing job: {str(e)}")

    async def generate_application(self, job: JobResult, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate application content using LangChain"""
        try:
            application = await self.apply_chain.arun(
                job_title=analysis["job_details"]["title"],
                company=job.company,
                location=job.location,
                requirements_analysis=analysis["requirements_analysis"]
            )

            return {
                "cover_letter": application,
                "resume_highlights": application  # You might want to split this into separate sections
            }
        except Exception as e:
            raise Exception(f"Error generating application: {str(e)}")

    async def process_job_application(self, job: JobResult) -> Dict[str, Any]:
        """Process a complete job application"""
        try:
            # Analyze the job
            analysis = await self.analyze_job(job)

            # Generate application content
            application = await self.generate_application(job, analysis)

            return {
                "job_analysis": analysis,
                "application_content": application
            }
        except Exception as e:
            raise Exception(f"Error processing job application: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        pass