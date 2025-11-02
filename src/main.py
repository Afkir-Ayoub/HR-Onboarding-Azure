import os
import logging
from openai import AzureOpenAI
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.azureaisearch import AzureAISearchVectorStore
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# --- Initial Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Azure & LlamaIndex Config ---
def initialize_query_engine():
    """
    Initializes and returns a LlamaIndex query engine connected to Azure services.
    """
    try:
        # Azure AI Search settings
        AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
        AZURE_AI_SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")

        # Azure OpenAI settings
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

        AZURE_OPENAI_DEPLOYMENT_NAME_LLM = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_LLM")
        AZURE_OPENAI_API_VERSION_LLM = os.getenv("AZURE_OPENAI_API_VERSION_LLM")

        AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING")
        AZURE_OPENAI_API_VERSION_EMBEDDING = os.getenv("AZURE_OPENAI_API_VERSION_EMBEDDING")
        
        # Configure LlamaIndex settings
        Settings.llm = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME_LLM,
            api_version=AZURE_OPENAI_API_VERSION_LLM,
        )
        Settings.embed_model = AzureOpenAIEmbedding(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING,
            api_version=AZURE_OPENAI_API_VERSION_EMBEDDING,
        )

        # Connect to the Azure AI Search Vector Store
        index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY))
        vector_store = AzureAISearchVectorStore(
            search_or_index_client=index_client,
            index_name=AZURE_AI_SEARCH_INDEX_NAME,
            id_field_key="id",
            chunk_field_key="chunk",
            embedding_field_key="embedding",
            embedding_dimensionality=1536,
            metadata_string_field_key="metadata",
            doc_id_field_key="doc_id",
        )

        # Build the index and query engine
        index = VectorStoreIndex.from_vector_store(vector_store)
        query_engine = index.as_query_engine(verbose=True)
        
        logging.info("Successfully initialized query engine.")
        return query_engine

    except Exception as e:
        logging.error(f"Failed to initialize query engine: {e}")
        return None

query_engine = initialize_query_engine()

# --- FastAPI ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

app = FastAPI(
    title="AI HR Onboarding Assistant API",
    description="An API for interacting with the AI HR Onboarding Assistant.",
    version="0.1.0",
)

@app.get("/")
def read_root():
    """A simple endpoint to test if the API is running."""
    return {"status": "API is running"}

@app.post("/chat", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest):
    """
    Handles a chat request from the user and returns a response from the AI.
    """
    if not query_engine:
        return {"reply": "Error: Query engine is not configured."}

    logging.info(f"Received query: {request.message}")

    # Query the engine with the user's message
    response = query_engine.query(request.message)
    
    reply_text = str(response)
    
    logging.info(f"Generated response: {reply_text}")

    return ChatResponse(reply=reply_text)