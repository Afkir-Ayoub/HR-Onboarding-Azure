"""Pydantic models for API requests and responses."""
from typing import List, Dict
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    message: str = Field(..., description="The user's message", min_length=1)
    history: List[Dict[str, str]] = Field(
        default_factory=list, description="Chat history"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    reply: str = Field(..., description="The assistant's response")


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    
    success: bool = Field(..., description="Whether the upload and ingestion was successful")
    message: str = Field(..., description="Status message")
    filename: str = Field(..., description="Name of the uploaded file")
    file_path: str = Field(..., description="Path where the file was saved")
    documents_ingested: int = Field(default=0, description="Number of documents ingested into the vector store")
