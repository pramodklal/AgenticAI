from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "")
    cosmos_database_name: str = os.getenv("COSMOS_DATABASE_NAME", "healthcoach")
    cosmos_state_container: str = os.getenv("COSMOS_STATE_CONTAINER", "conversation_state")
    cosmos_user_container: str = os.getenv("COSMOS_USER_CONTAINER", "user_profiles")
    cosmos_workout_container: str = os.getenv("COSMOS_WORKOUT_CONTAINER", "workout_logs")
    azure_search_endpoint: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    azure_search_api_key: str = os.getenv("AZURE_SEARCH_API_KEY", "")
    azure_search_wellness_index: str = os.getenv("AZURE_SEARCH_WELLNESS_INDEX", "wellness-index")
    azure_search_nutrition_index: str = os.getenv("AZURE_SEARCH_NUTRITION_INDEX", "nutrition-index")
    azure_storage_connection_string: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    azure_file_share_name: str = os.getenv("AZURE_FILE_SHARE_NAME", "wellness-docs")

    @property
    def has_azure_openai(self) -> bool:
        return all(
            [self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_openai_deployment]
        )

    @property
    def has_cosmos(self) -> bool:
        return bool(self.cosmos_endpoint)

    @property
    def has_ai_search(self) -> bool:
        return bool(self.azure_search_endpoint and self.azure_search_api_key)


settings = Settings()
