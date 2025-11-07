"""Data ingestion script for loading documents into Azure AI Search."""
import logging
import sys
from pathlib import Path
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

# Works both as module and direct scirpt
try:
    from backend.config import settings
except ImportError:
    from config import settings

# --- Initial Setup ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Get the project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# --- Ingestion Process ---
def main():
    """
    Main function to load documents, create an index, and store it in Azure AI Search.
    """
    logging.info("Starting data ingestion process...")

    # Setup LlamaIndex
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
    
    # Load Docs
    try:
        documents = SimpleDirectoryReader(str(DATA_DIR)).load_data()
        if not documents:
            logging.error(f"No documents found in '{DATA_DIR}'. Please check the directory.")
            return
        logging.info(f"Loaded {len(documents)} document(s) from '{DATA_DIR}'.")
    except Exception as e:
        logging.error(f"Failed to load documents: {e}")
        return

    # Setup Azure AI Search Vector Store
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
    logging.info("Azure AI Search vector store configured.")

    # Create and Ingest the Index
    logging.info(f"Creating index '{settings.azure_ai_search_index_name}' and ingesting documents...")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Creates the embeddings and stores them in Azure AI Search
    VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    logging.info("Successfully created and ingested index.")


if __name__ == "__main__":
    main()

