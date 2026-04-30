from __future__ import annotations

from langchain_openai import AzureChatOpenAI

from healthcoach.config import settings


def get_chat_model() -> AzureChatOpenAI | None:
    if not settings.has_azure_openai:
        return None

    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version,
        temperature=0.2,
    )
