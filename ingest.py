import os
import logging
import sys
from dotenv import load_dotenv
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

# --- Initial Setup ---
load_dotenv()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# --- Configuration ---
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
AZURE_AI_SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

AZURE_OPENAI_DEPLOYMENT_NAME_LLM = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_LLM")
AZURE_OPENAI_API_VERSION_LLM = os.getenv("AZURE_OPENAI_API_VERSION_LLM")

AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING")
AZURE_OPENAI_API_VERSION_EMBEDDING = os.getenv("AZURE_OPENAI_API_VERSION_EMBEDDING")

DATA_DIR = "data"

# --- Ingestion Process ---
def main():
    """
    Main function to load documents, create an index, and store it in Azure AI Search.
    """
    logging.info("Starting data ingestion process...")

    # Setup LlamaIndex
    llm = AzureOpenAI(
        model="gpt-4o-mini",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME_LLM,
        api_version=AZURE_OPENAI_API_VERSION_LLM,
    )
    embed_model = AzureOpenAIEmbedding(
        model="text-embedding-ada-002",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING,
        api_version=AZURE_OPENAI_API_VERSION_EMBEDDING,
    )
    
    # Set global settings
    Settings.llm = llm
    Settings.embed_model = embed_model
    
    # Load Docs
    try:
        documents = SimpleDirectoryReader(DATA_DIR).load_data()
        if not documents:
            logging.error(f"No documents found in '{DATA_DIR}'. Please check the directory.")
            return
        logging.info(f"Loaded {len(documents)} document(s) from '{DATA_DIR}'.")
    except Exception as e:
        logging.error(f"Failed to load documents: {e}")
        return

    # Setup Azure AI Search Vector Store
    index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY))
    vector_store = AzureAISearchVectorStore(
        search_or_index_client=index_client,
        index_name=AZURE_AI_SEARCH_INDEX_NAME,
        endpoint=AZURE_AI_SEARCH_ENDPOINT,
        key=AZURE_AI_SEARCH_KEY,
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
    logging.info(f"Creating index '{AZURE_AI_SEARCH_INDEX_NAME}' and ingesting documents...")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Creates the embeddings and stores them in Azure AI Search
    VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    logging.info("Successfully created and ingested index.")

if __name__ == "__main__":
    main()