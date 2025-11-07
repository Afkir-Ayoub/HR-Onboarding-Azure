"""Agent service for initializing and managing the LangChain agent."""
import datetime
import logging
from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
from llama_index.core import Settings as LlamaIndexSettings
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from ..config import settings
from .vector_store import create_query_engine
from ..tools import hr_knowledge_base, create_calendar_event, list_calendar_events
from ..state import app_state

logger = logging.getLogger(__name__)


def initialize_agent():
    """
    Initializes and returns a LangChain agent with LlamaIndex RAG tool.
    Uses the modern create_agent function which builds on LangGraph internally.
    """
    try:
        # Configure LlamaIndex LLM (for query engine)
        llama_llm = AzureOpenAI(
            model=settings.azure_openai_deployment_name_llm,
            deployment_name=settings.azure_openai_deployment_name_llm,
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version_llm,
            temperature=0.0,
        )

        # Configure LlamaIndex Embedding Model
        embed_model = AzureOpenAIEmbedding(
            model=settings.azure_openai_deployment_name_embedding,
            deployment_name=settings.azure_openai_deployment_name_embedding,
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version_embedding,
        )

        # Set global LlamaIndex settings
        LlamaIndexSettings.llm = llama_llm
        LlamaIndexSettings.embed_model = embed_model

        # Configure LangChain LLM (for agent)
        langchain_llm = AzureChatOpenAI(
            deployment_name=settings.azure_openai_deployment_name_llm,
            openai_api_version=settings.azure_openai_api_version_llm,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            temperature=0.0,
        )

        # Create query engine and store in app state
        query_engine = create_query_engine()
        app_state.query_engine = query_engine

        # Create agent using modern create_agent function
        agent = create_agent(
            model=langchain_llm,
            tools=[hr_knowledge_base, create_calendar_event, list_calendar_events],
            system_prompt=(
                "You are a helpful HR assistant for new employees. "
                "Use the hr_knowledge_base tool to answer questions about company policies, "
                "onboarding, benefits, and HR procedures. "
                "Always search the knowledge base before answering HR-related questions. "
                "If the information isn't in the knowledge base, politely say so. "
                "Keep your answers concise and helpful."
                f"Today is {datetime.datetime.now(datetime.timezone.utc)}."
            ),
        )

        logger.info("Successfully initialized LangChain agent with LlamaIndex RAG / Microsoft Calendar.")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        raise

