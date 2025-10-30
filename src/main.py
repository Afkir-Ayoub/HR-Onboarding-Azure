import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# --- 1. CONFIGURE AZURE OPENAI CLIENT ---
# Best practice: create the client once and reuse it
try:
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
except Exception as e:
    print(f"Error configuring Azure OpenAI client: {e}")
    client = None
    AZURE_DEPLOYMENT_NAME = None

# --- 2. DEFINE DATA MODELS ---
# Pydantic models for structured request and response data
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# --- 3. SETUP FASTAPI APP ---
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
    if not client:
        return {"reply": "Error: Azure OpenAI client is not configured."}

    completion = client.chat.completions.create(
        model=AZURE_DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful HR assistant.",
            },
            {
                "role": "user",
                "content": request.message,
            },
        ],
    )
    
    reply = completion.choices[0].message.content
    return {"reply": reply}