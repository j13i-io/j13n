from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import AsyncGenerator, Dict, Any, Optional, List
from ..services.document_service import DocumentService
from ..config.settings import get_settings
from fastapi.responses import JSONResponse
from ..models.document_models import DocumentType, DocumentInfo, DocumentListResponse
import asyncio

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

async def get_document_service() -> AsyncGenerator[DocumentService, None]:
    service = None
    try:
        service = DocumentService()
        yield service
    finally:
        if service:
            await service.cleanup()

@router.post("/upload/{document_type}", response_model=DocumentInfo)
async def upload_document(
    document_type: DocumentType,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    service: DocumentService = Depends(get_document_service)
) -> DocumentInfo:
    """
    Upload a document (resume or cover letter) with optimized handling
    """
    try:
        # Validate content type
        allowed_types = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        }

        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed types: PDF, DOC, DOCX, TXT"
            )

        # Process upload
        result = await service.save_document(file, document_type)

        # Add cleanup task
        if background_tasks:
            background_tasks.add_task(file.close)

        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    document_type: Optional[DocumentType] = None,
    service: DocumentService = Depends(get_document_service)
) -> DocumentListResponse:
    """
    List all documents with optional filtering by type
    """
    try:
        return await service.list_documents(document_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.get("/{filename}", response_model=DocumentInfo)
async def get_document(
    filename: str,
    service: DocumentService = Depends(get_document_service)
) -> DocumentInfo:
    """
    Get document information
    """
    try:
        result = await service.get_document(filename)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving document: {str(e)}"
        )

@router.delete("/{filename}")
async def delete_document(
    filename: str,
    background_tasks: BackgroundTasks = None,
    service: DocumentService = Depends(get_document_service)
) -> Dict[str, bool]:
    """
    Delete a document
    """
    try:
        success = await service.delete_document(filename)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )