"""Configuration management for the HR Onboarding Assistant."""
import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


def validate_env_vars() -> Dict[str, str]:
    """Validate and return all required environment variables."""
    required_vars = [
        "AZURE_AI_SEARCH_ENDPOINT",
        "AZURE_AI_SEARCH_KEY",
        "AZURE_AI_SEARCH_INDEX_NAME",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT_NAME_LLM",
        "AZURE_OPENAI_API_VERSION_LLM",
        "AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING",
        "AZURE_OPENAI_API_VERSION_EMBEDDING",
        "MS_GRAPH_CLIENT_ID",
        "MS_GRAPH_TENANT_ID",
        "MS_GRAPH_CLIENT_SECRET",
    ]

    env_vars = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            env_vars[var] = value

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return env_vars


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings by validating and loading environment variables."""
        env_vars = validate_env_vars()
        
        # Azure AI Search
        self.azure_ai_search_endpoint = env_vars["AZURE_AI_SEARCH_ENDPOINT"]
        self.azure_ai_search_key = env_vars["AZURE_AI_SEARCH_KEY"]
        self.azure_ai_search_index_name = env_vars["AZURE_AI_SEARCH_INDEX_NAME"]
        
        # Azure OpenAI
        self.azure_openai_endpoint = env_vars["AZURE_OPENAI_ENDPOINT"]
        self.azure_openai_api_key = env_vars["AZURE_OPENAI_API_KEY"]
        self.azure_openai_deployment_name_llm = env_vars["AZURE_OPENAI_DEPLOYMENT_NAME_LLM"]
        self.azure_openai_api_version_llm = env_vars["AZURE_OPENAI_API_VERSION_LLM"]
        self.azure_openai_deployment_name_embedding = env_vars["AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING"]
        self.azure_openai_api_version_embedding = env_vars["AZURE_OPENAI_API_VERSION_EMBEDDING"]
        
        # Microsoft Graph
        self.ms_graph_client_id = env_vars["MS_GRAPH_CLIENT_ID"]
        self.ms_graph_tenant_id = env_vars["MS_GRAPH_TENANT_ID"]
        self.ms_graph_client_secret = env_vars["MS_GRAPH_CLIENT_SECRET"]


# Global settings instance
settings = Settings()

