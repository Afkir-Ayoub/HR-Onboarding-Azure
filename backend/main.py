import os
import logging
from typing import List, Dict
from openai import AzureOpenAI
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.vector_stores.azureaisearch import AzureAISearchVectorStore
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# --- Initial Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

global_memory = ChatMemoryBuffer.from_defaults(token_limit=3000)

# --- Azure & LlamaIndex Config ---
def initialize_chat_engine():
    """
    Initializes and returns a LlamaIndex chat engine connected to Azure services.
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

        # Build the index and chat engine
        index = VectorStoreIndex.from_vector_store(vector_store)

        # Create the chat engine
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=global_memory,
            system_prompt="You are a friendly and helpful assistant. Answer the user's questions based on the context provided. Answer in a concise, short and clear manner.",
            verbose=True,
        )
                
        logging.info("Successfully initialized chat engine.")
        return chat_engine

    except Exception as e:
        logging.error(f"Failed to initialize chat engine: {e}")
        return None

chat_engine = initialize_chat_engine()

# --- FastAPI ---
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]

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
    if not chat_engine:
        return ChatResponse(reply="Error: Chat engine is not available.")

    logging.info(f"Received message: {request.message} with history length: {len(request.history)}")
    
    chat_history = [
        ChatMessage(
            role=MessageRole.ASSISTANT if msg["role"] == "assistant" else MessageRole.USER,
            content=msg["content"]
        ) for msg in request.history
    ]

    global_memory.set(chat_history)

    logging.info(f"Received message: '{request.message}'. History has {len(global_memory.get())} messages.")

    # Return response
    response = chat_engine.chat(request.message)

    reply_text = str(response)
    
    logging.info(f"Generated response: {reply_text}")

    return ChatResponse(reply=reply_text)