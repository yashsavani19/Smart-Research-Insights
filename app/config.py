import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class CoreApiSettings:
    base_url: str = "https://api.core.ac.uk/v3"
    works_search_path: str = "/search/works"
    api_key: str = os.getenv("CORE_API_KEY", "")
    default_page_size: int = int(os.getenv("CORE_DEFAULT_PAGE_SIZE", "10"))
    max_retries: int = int(os.getenv("CORE_MAX_RETRIES", "5"))
    timeout_seconds: int = int(os.getenv("CORE_TIMEOUT_SECONDS", "30"))


settings = CoreApiSettings()


def get_auth_header() -> dict:
    if not settings.api_key:
        raise RuntimeError(
            "CORE_API_KEY is not set. Add it to your environment or .env file."
        )
    return {"Authorization": settings.api_key}


