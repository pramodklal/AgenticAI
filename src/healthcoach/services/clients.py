from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient

from healthcoach.config import settings


def get_cosmos_client() -> CosmosClient | None:
    if not settings.has_cosmos:
        return None

    return CosmosClient(settings.cosmos_endpoint, credential=settings.azure_openai_api_key)


def get_wellness_search_client() -> SearchClient | None:
    if not settings.has_ai_search:
        return None

    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_wellness_index,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )


def get_nutrition_search_client() -> SearchClient | None:
    if not settings.has_ai_search:
        return None

    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_nutrition_index,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
