"""Service for ingesting documents into Azure AI Search."""
import logging
from pathlib import Path
from typing import List
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.vector_stores.azureaisearch import AzureAISearchVectorStore, IndexManagement
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from ..config import settings

logger = logging.getLogger(__name__)


def _setup_llamaindex_settings():
    """Setup LlamaIndex global settings for LLM and embeddings."""
    Settings.llm = AzureOpenAI(
        model="gpt-4o-mini",
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment_name=settings.azure_openai_deployment_name_llm,
        api_version=settings.azure_openai_api_version_llm,
    )
    Settings.embed_model = AzureOpenAIEmbedding(
        model="text-embedding-ada-002",
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment_name=settings.azure_openai_deployment_name_embedding,
        api_version=settings.azure_openai_api_version_embedding,
    )


def _create_vector_store() -> AzureAISearchVectorStore:
    """Create and return an Azure AI Search vector store instance."""
    index_client = SearchIndexClient(
        endpoint=settings.azure_ai_search_endpoint,
        credential=AzureKeyCredential(settings.azure_ai_search_key)
    )
    
    vector_store = AzureAISearchVectorStore(
        search_or_index_client=index_client,
        index_name=settings.azure_ai_search_index_name,
        endpoint=settings.azure_ai_search_endpoint,
        key=settings.azure_ai_search_key,
        index_management=IndexManagement.CREATE_IF_NOT_EXISTS,
        id_field_key="id",
        chunk_field_key="chunk",
        embedding_field_key="embedding",
        embedding_dimensionality=1536,
        metadata_string_field_key="metadata",
        doc_id_field_key="doc_id",
    )
    
    return vector_store


def ingest_documents(file_paths: List[str]) -> dict:
    """
    Ingest one or more documents into Azure AI Search.
    
    Args:
        file_paths: List of file paths to ingest
        
    Returns:
        dict with success status and message
    """
    try:
        _setup_llamaindex_settings()
        
        documents = []
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            try:
                # Load document from the file
                file_docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
                documents.extend(file_docs)
                logger.info(f"Loaded document from: {file_path}")
            except Exception as e:
                logger.error(f"Failed to load document from {file_path}: {e}")
                continue
        
        if not documents:
            return {
                "success": False,
                "message": "No documents were successfully loaded.",
                "documents_ingested": 0,
            }
        
        # Setup vector store
        vector_store = _create_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Ingest documents into Azure AI Search
        VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        
        logger.info(f"Successfully ingested {len(documents)} document(s) into Azure AI Search.")
        
        return {
            "success": True,
            "message": f"Successfully ingested {len(documents)} document(s).",
            "documents_ingested": len(documents),
        }
        
    except Exception as e:
        logger.error(f"Error during document ingestion: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to ingest documents: {str(e)}",
            "documents_ingested": 0,
        }


def ingest_single_document(file_path: str) -> dict:
    """
    Ingest a single document into Azure AI Search.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        dict with success status and message
    """
    return ingest_documents([file_path])

