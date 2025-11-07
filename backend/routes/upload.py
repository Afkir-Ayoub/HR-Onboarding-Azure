"""File upload API routes."""
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import UploadResponse
from ..services.ingestion_service import ingest_single_document

logger = logging.getLogger(__name__)

router = APIRouter()

# Get the project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and ingest it into Azure AI Search.
    
    The file will be saved to the data directory and then ingested
    into the vector store for use in the RAG system.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Save file to data directory
    file_path = DATA_DIR / file.filename
    
    try:
        # Read file content
        contents = await file.read()
        
        # Write to disk
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"File saved to: {file_path}")
        
        # Ingest the document into Azure AI Search
        ingestion_result = ingest_single_document(str(file_path))
        
        if ingestion_result["success"]:
            return UploadResponse(
                success=True,
                message=ingestion_result["message"],
                filename=file.filename,
                file_path=str(file_path),
                documents_ingested=ingestion_result["documents_ingested"],
            )
        else:
            # File was saved but ingestion failed
            logger.error(f"File saved but ingestion failed: {ingestion_result['message']}")
            return UploadResponse(
                success=False,
                message=f"File uploaded successfully but ingestion failed: {ingestion_result['message']}",
                filename=file.filename,
                file_path=str(file_path),
                documents_ingested=0,
            )
            
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        # Clean up file if it was partially written
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload and process file: {str(e)}"
        )

