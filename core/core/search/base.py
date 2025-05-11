from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from ..config.settings import get_settings

class BaseSearchService(ABC):
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            api_key=self.settings.OPENAI_API_KEY
        )
        self._setup_chains()

    def _setup_chains(self):
        # Chain for optimizing search query for job postings
        query_optimize_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at optimizing search queries for job postings.
            Transform the input query to specifically target job posting URLs.
            Add necessary keywords and operators to get direct job posting results.
            Return a JSON object with:
            - optimized_query: the optimized search query
            - site_restrictions: list of job board domains to include/exclude
            - file_type: if any specific file type should be targeted
            - time_range: if any specific time range should be used"""),
            ("user", "Original Query: {query}\n\nOptimize this query for job posting URLs.")
        ])
        self.query_optimize_chain = LLMChain(llm=self.llm, prompt=query_optimize_prompt)

        # Chain for filtering and ranking job URLs
        job_url_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at identifying job posting URLs from search results.
            Analyze the URLs and their titles/descriptions to determine if they are actual job postings.
            Return a JSON array of objects with:
            - url: the URL
            - is_job_posting: boolean indicating if it's a job posting
            - confidence: number between 0 and 1 indicating confidence
            - reason: brief explanation of why it is/isn't a job posting
            Prioritize URLs that are direct job postings over job board search results or company career pages."""),
            ("user", "Search Results: {results}\n\nIdentify job posting URLs.")
        ])
        self.job_url_chain = LLMChain(llm=self.llm, prompt=job_url_prompt)

    async def optimize_query(self, query: str) -> Dict[str, Any]:
        """Optimize search query for job postings"""
        try:
            # Get LLM optimization
            optimization = await self.query_optimize_chain.arun(query=query)

            # Common job board domains to include
            job_boards = [
                'linkedin.com/jobs',
                'indeed.com/job',
                'glassdoor.com/Job',
                'monster.com/job',
                'careerbuilder.com/job',
                'dice.com/job',
                'ziprecruiter.com/job',
                'simplyhired.com/job'
            ]

            # Build site restrictions
            site_restrictions = ' OR '.join([f'site:{board}' for board in job_boards])

            # Add common job posting indicators
            job_indicators = [
                'inurl:jobs',
                'inurl:job',
                'inurl:careers',
                'inurl:positions',
                'intitle:"job"',
                'intitle:"career"',
                'intitle:"position"'
            ]

            # Combine everything
            optimized_query = f"{query} ({site_restrictions}) ({' OR '.join(job_indicators)})"

            return {
                "original_query": query,
                "optimized_query": optimized_query,
                "site_restrictions": job_boards,
                "file_type": None,  # Job postings are typically HTML
                "time_range": "past_month"  # Default to recent postings
            }
        except Exception as e:
            raise Exception(f"Error optimizing query: {str(e)}")

    async def filter_job_urls(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank URLs to prioritize job postings"""
        try:
            # Format results for the LLM
            formatted_results = [
                f"URL: {r.get('url', '')}\nTitle: {r.get('title', '')}\nDescription: {r.get('description', '')}"
                for r in results
            ]

            # Get LLM analysis
            analysis = await self.job_url_chain.arun(results="\n\n".join(formatted_results))

            # Parse and filter results
            filtered_results = []
            for result in results:
                url = result.get('url', '')
                # Check for direct job posting URLs
                if any(pattern in url.lower() for pattern in [
                    '/jobs/view/', '/job/', '/careers/', '/positions/',
                    '/job-details/', '/job-description/', '/job-posting/',
                    '/job-opportunity/', '/job-opening/'
                ]):
                    result['is_job_posting'] = True
                    result['confidence'] = 0.9
                    filtered_results.append(result)
                # Check for job board search results
                elif any(board in url.lower() for board in [
                    'linkedin.com/jobs/search',
                    'indeed.com/jobs',
                    'glassdoor.com/Jobs',
                    'monster.com/jobs'
                ]):
                    result['is_job_posting'] = False
                    result['confidence'] = 0.3
                    filtered_results.append(result)

            # Sort by confidence and is_job_posting
            filtered_results.sort(key=lambda x: (x.get('is_job_posting', False), x.get('confidence', 0)), reverse=True)

            return filtered_results
        except Exception as e:
            raise Exception(f"Error filtering job URLs: {str(e)}")

    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for job postings"""
        pass