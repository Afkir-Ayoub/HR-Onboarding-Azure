"""Chat API routes."""
import logging
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing import List
from ..models import ChatRequest, ChatResponse
from ..state import app_state

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def read_root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "AI HR Onboarding Assistant",
        "version": "1.0.0",
    }


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat endpoint that processes user messages and returns AI responses.

    The agent uses a RAG system backed by Azure AI Search to answer questions
    about HR policies, onboarding procedures, and company information.
    """
    if not app_state.agent:
        logger.error("Agent not available")
        raise HTTPException(
            status_code=503, detail="Service unavailable: Agent is not initialized."
        )

    # Convert history to LangChain message format
    chat_history: List[BaseMessage] = []
    for msg in request.history:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        if not content:
            continue
        
        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_history.append(AIMessage(content=content))

    try:
        # Build the full message list
        all_messages = chat_history + [HumanMessage(content=request.message)]

        # Invoke agent using the modern create_agent API
        result = await app_state.agent.ainvoke({"messages": all_messages})

        # Extract the last message from the result
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            reply = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
        else:
            reply = "I'm sorry, I couldn't generate a response."

        return ChatResponse(reply=reply)

    except Exception as e:
        logger.error(f"Error during agent invocation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request. Please try again.",
        )

