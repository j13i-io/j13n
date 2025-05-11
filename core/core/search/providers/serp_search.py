from typing import List

from langchain.utilities import SerpAPIWrapper

from ..base.search_service import BaseSearchService, SearchRequest, SearchResult
from ...config.settings import get_settings


class SerpSearchService(BaseSearchService):
    def __init__(self):
        self.settings = get_settings()
        self.search = SerpAPIWrapper(serpapi_api_key=self.settings.SERPAPI_API_KEY)
        self._thread_pool = None

    @property
    def provider_name(self) -> str:
        return "serpapi"

    async def search(self, request: SearchRequest) -> List[SearchResult]:
        try:
            # Perform the search with the exact query provided
            results = await self._run_in_threadpool(
                self.search.results,
                request.query,
                request.num_results
            )

            # Convert raw results to SearchResult objects
            return [
                SearchResult(
                    title=result.get("title", ""),
                    link=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    source=result.get("source", ""),
                    metadata={
                        "position": result.get("position"),
                        "date": result.get("date"),
                        "location": result.get("location")
                    }
                )
                for result in results.get("organic_results", [])
            ]
        except Exception as e:
            raise Exception(f"SerpAPI search error: {str(e)}")

    async def _run_in_threadpool(self, func, *args):
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, func, *args)

    async def cleanup(self) -> None:
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
