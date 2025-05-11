from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str
    num_results: int = 10
    filters: Optional[Dict[str, Any]] = None


class BaseSearchService(ABC):
    """Abstract base class for search services"""

    @abstractmethod
    async def search(self, request: SearchRequest) -> List[SearchResult]:
        """
        Perform a search using the provided request parameters

        Args:
            request: SearchRequest object containing search parameters

        Returns:
            List of SearchResult objects
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup any resources used by the search service"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the search provider"""
        pass
