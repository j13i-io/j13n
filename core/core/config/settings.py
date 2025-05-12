from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Job Search API"
    DEBUG: bool = True
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")
    API_PREFIX: str = "/api/v1"

    # Property aliases for consistent naming
    @property
    def serpapi_key(self) -> str:
        return self.SERPAPI_API_KEY

    @property
    def google_api_key(self) -> str:
        return self.GOOGLE_API_KEY

    @property
    def google_cse_id(self) -> str:
        return self.GOOGLE_CSE_ID

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
