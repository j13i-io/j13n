from typing import Dict, Any
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from ..models.application_models import JobAnalysis, ApplicationResponse
from ..config.settings import get_settings
from ..scraping import JobScrappingService, FormScrapingService

class JobAnalysisService:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            api_key=self.settings.OPENAI_API_KEY
        )
        self.job_scraper = JobScrappingService()
        self.form_scraper = FormScrapingService()
        self._setup_chains()

    def _setup_chains(self):
        # Chain for identifying form fields from job posting
        form_fields_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing job postings and identifying required application form fields.
            Analyze the job posting and identify ONLY the form fields that an applicant needs to fill out.
            Return a JSON object where each key is a form field name and the value is an object with:
            - required: boolean indicating if the field is mandatory
            - field_type: type of input needed (text, number, date, select, etc.)
            - description: brief description of what should go in this field
            Do not include any predefined fields or assumptions. Only include fields explicitly mentioned in the job posting."""),
            ("user", "Content: {content}\n\nIdentify the required application form fields.")
        ])
        self.form_fields_chain = LLMChain(llm=self.llm, prompt=form_fields_prompt)

    async def identify_form_fields(self, content: str) -> Dict[str, Any]:
        """Use LLM to identify required form fields from job posting"""
        try:
            return await self.form_fields_chain.arun(content=content)
        except Exception as e:
            raise Exception(f"Error identifying form fields: {str(e)}")

    async def analyze_job_posting(self, job_url: str) -> ApplicationResponse:
        """Analyze a job posting and identify form fields"""
        try:
            # Scrape job posting content
            job_data = await self.job_scraper.scrape(job_url)

            # Try to scrape actual form fields if available
            try:
                form_data = await self.form_scraper.scrape(job_url)
                form_fields = form_data["form_fields"]
            except:
                # If form scraping fails, use LLM to identify fields
                form_fields = await self.identify_form_fields(job_data["content"])

            # Create analysis with URL and form fields
            analysis = JobAnalysis(
                url=job_url,
                form_fields=form_fields
            )

            return ApplicationResponse(
                analysis=analysis,
                success=True,
                message="Job posting analyzed successfully"
            )
        except Exception as e:
            raise Exception(f"Error analyzing job posting: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        pass