from typing import List
import re
from langchain.utilities import SerpAPIWrapper
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from ..base.job_search_service import BaseJobSearchService, JobSearchRequest, JobSearchResult
from ..base.search_service import SearchResult
from ...config.settings import get_settings


class SerpJobSearchService(BaseJobSearchService):
    def __init__(self):
        self.settings = get_settings()
        self.search = SerpAPIWrapper(serpapi_api_key=self.settings.SERPAPI_API_KEY)
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            openai_api_key=self.settings.OPENAI_API_KEY
        )
        self._thread_pool = None

    @property
    def provider_name(self) -> str:
        return "serpapi_jobs"

    async def optimize_search_query(self, request: JobSearchRequest) -> str:
        """Use LLM to optimize the search query for job search"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a job search expert. Your task is to optimize the given job search parameters
            into an effective search query. Focus on:
            1. Including relevant job titles and skills
            2. Adding location if specified
            3. Including company name if specified
            4. Adding job type if specified
            5. Including experience level if specified
            6. Adding salary expectations if specified
            7. Including remote work preference if specified
            8. Adding time constraints if specified

            Format the query to work well with search engines. Use quotes for exact phrases and site: operator
            for specific job sites when appropriate."""),
            ("user", "Job Title: {job_title}\nLocation: {location}\nCompany: {company}\n"
                    "Job Type: {job_type}\nExperience: {experience}\nSalary: {salary}\n"
                    "Remote: {remote}\nPosted Within: {posted_within}")
        ])

        # Format the prompt with the request parameters
        formatted_prompt = prompt.format_messages(
            job_title=request.job_title or "",
            location=request.location or "",
            company=request.company or "",
            job_type=request.job_type or "",
            experience=request.experience_level or "",
            salary=request.salary_range or "",
            remote="remote" if request.remote else "",
            posted_within=request.posted_within or ""
        )

        # Get optimized query from LLM
        response = await self.llm.agenerate([formatted_prompt])
        return response.generations[0][0].text.strip()

    async def extract_application_url(self, search_result: SearchResult) -> str:
        """Extract or generate the direct application URL from a search result"""
        # First try to find direct application links in the snippet
        application_patterns = [
            r'(https?://[^\s<>"]+?/apply[^\s<>"]*)',
            r'(https?://[^\s<>"]+?/jobs/apply[^\s<>"]*)',
            r'(https?://[^\s<>"]+?/careers/apply[^\s<>"]*)',
            r'(https?://[^\s<>"]+?/job-application[^\s<>"]*)'
        ]

        for pattern in application_patterns:
            if match := re.search(pattern, search_result.snippet):
                return match.group(1)

        # If no direct application link found, use the main link
        return search_result.link

    async def search(self, request: JobSearchRequest) -> List[JobSearchResult]:
        try:
            # Optimize the search query using LLM
            optimized_query = await self.optimize_search_query(request)

            # Perform the search with the optimized query
            results = await self._run_in_threadpool(
                self.search.results,
                optimized_query,
                request.num_results
            )

            # Convert raw results to JobSearchResult objects
            job_results = []
            for result in results.get("organic_results", []):
                # Extract application URL
                application_url = await self.extract_application_url(
                    SearchResult(
                        title=result.get("title", ""),
                        link=result.get("link", ""),
                        snippet=result.get("snippet", "")
                    )
                )

                # Create JobSearchResult
                job_result = JobSearchResult(
                    title=result.get("title", ""),
                    link=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    source=result.get("source", ""),
                    company_name=self._extract_company_name(result),
                    job_title=self._extract_job_title(result),
                    location=self._extract_location(result),
                    salary_range=self._extract_salary(result),
                    job_type=self._extract_job_type(result),
                    posted_date=self._extract_posted_date(result),
                    application_url=application_url,
                    job_description=result.get("snippet", ""),
                    metadata={
                        "position": result.get("position"),
                        "date": result.get("date"),
                        "location": result.get("location")
                    }
                )
                job_results.append(job_result)

            return job_results

        except Exception as e:
            raise Exception(f"SerpAPI job search error: {str(e)}")

    def _extract_company_name(self, result: dict) -> str:
        """Extract company name from search result"""
        title = result.get("title", "")
        # Common patterns for company names in job titles
        patterns = [
            r'^([^\-|]*)',  # Everything before first dash or pipe
            r'at\s+([^\-|]*)',  # Text after "at"
            r'with\s+([^\-|]*)'  # Text after "with"
        ]

        for pattern in patterns:
            if match := re.search(pattern, title):
                return match.group(1).strip()
        return ""

    def _extract_job_title(self, result: dict) -> str:
        """Extract job title from search result"""
        title = result.get("title", "")
        # Remove company name and common suffixes
        title = re.sub(r'\s*[-|]\s*.*$', '', title)
        title = re.sub(r'\s*at\s+.*$', '', title)
        return title.strip()

    def _extract_location(self, result: dict) -> str:
        """Extract location from search result"""
        return result.get("location", "")

    def _extract_salary(self, result: dict) -> str:
        """Extract salary information from search result"""
        snippet = result.get("snippet", "")
        salary_pattern = r'\$[\d,]+(?:-\$[\d,]+)?(?:\s*(?:per year|per hour|per month|annually|hourly))?'
        if match := re.search(salary_pattern, snippet):
            return match.group(0)
        return ""

    def _extract_job_type(self, result: dict) -> str:
        """Extract job type from search result"""
        snippet = result.get("snippet", "")
        job_types = ["Full-time", "Part-time", "Contract", "Temporary", "Internship"]
        for job_type in job_types:
            if job_type.lower() in snippet.lower():
                return job_type
        return ""

    def _extract_posted_date(self, result: dict) -> str:
        """Extract posted date from search result"""
        return result.get("date", "")

    async def _run_in_threadpool(self, func, *args):
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, func, *args)

    async def cleanup(self) -> None:
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)