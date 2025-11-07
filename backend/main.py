"""Main FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from .services.agent_service import initialize_agent
from .state import app_state
from .routes.chat import router as chat_router
from .routes.upload import router as upload_router
from .routes.auth import router as auth_router

# --- Initial Setup ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Initializing application...")
    try:
        app_state.agent = initialize_agent()
        logger.info("Application initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield
    logger.info("Shutting down application...")


# --- FastAPI App ---
app = FastAPI(
    title="AI HR Onboarding Assistant API",
    description="An API for interacting with the AI HR Onboarding Assistant powered by LlamaIndex RAG and LangChain agents.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routes
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(auth_router)
