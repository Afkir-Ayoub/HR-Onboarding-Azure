"""Vector store service for Azure AI Search integration."""
import logging
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.azureaisearch import AzureAISearchVectorStore
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from ..config import settings

logger = logging.getLogger(__name__)


def create_vector_store() -> AzureAISearchVectorStore:
    """Create and return an Azure AI Search vector store instance."""
    index_client = SearchIndexClient(
        endpoint=settings.azure_ai_search_endpoint,
        credential=AzureKeyCredential(settings.azure_ai_search_key),
    )

    vector_store = AzureAISearchVectorStore(
        search_or_index_client=index_client,
        index_name=settings.azure_ai_search_index_name,
        id_field_key="id",
        chunk_field_key="chunk",
        embedding_field_key="embedding",
        embedding_dimensionality=1536,
        metadata_string_field_key="metadata",
        doc_id_field_key="doc_id",
    )

    return vector_store


def create_query_engine():
    """Create and return a LlamaIndex query engine from the vector store."""
    vector_store = create_vector_store()
    index = VectorStoreIndex.from_vector_store(vector_store)
    
    query_engine = index.as_query_engine(
        similarity_top_k=3, response_mode="compact"
    )
    
    logger.info("Query engine created successfully")
    return query_engine

