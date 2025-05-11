from typing import Dict, Any, Optional, List
import os
from fastapi import UploadFile
from ..config.settings import get_settings
import aiofiles
import uuid
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import magic
import aiofiles.os
from pathlib import Path
from ..models.document_models import DocumentType, DocumentInfo, DocumentListResponse

class DocumentService:
    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        self._ensure_upload_dir()
        self.chunk_size = 1024 * 1024  # 1MB chunks
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

    def _ensure_upload_dir(self):
        """Ensure the upload directory exists"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    async def _validate_file_type(self, file_path: str) -> bool:
        """Validate file type using python-magic"""
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            allowed_types = {
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain"
            }
            return file_type in allowed_types
        except Exception:
            return False

    async def _stream_file(self, file: UploadFile, file_path: str) -> int:
        """Stream file content in chunks"""
        total_size = 0
        async with aiofiles.open(file_path, 'wb') as out_file:
            while True:
                chunk = await file.read(self.chunk_size)
                if not chunk:
                    break
                if total_size + len(chunk) > self.max_file_size:
                    await aiofiles.os.remove(file_path)
                    raise ValueError("File size exceeds maximum limit")
                await out_file.write(chunk)
                total_size += len(chunk)
        return total_size

    async def save_document(self, file: UploadFile, document_type: DocumentType) -> DocumentInfo:
        """
        Save an uploaded document with optimized streaming

        Args:
            file: The uploaded file
            document_type: Type of document (resume/cover_letter)

        Returns:
            DocumentInfo containing file information
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_extension = os.path.splitext(file.filename)[1]
            new_filename = f"{document_type.value}_{timestamp}_{unique_id}{file_extension}"
            file_path = os.path.join(self.upload_dir, new_filename)

            # Stream file content
            total_size = await self._stream_file(file, file_path)

            # Validate file type
            if not await self._validate_file_type(file_path):
                await aiofiles.os.remove(file_path)
                raise ValueError("Invalid file type")

            return DocumentInfo(
                filename=new_filename,
                original_filename=file.filename,
                file_path=file_path,
                document_type=document_type,
                size=total_size,
                content_type=file.content_type
            )
        except Exception as e:
            # Cleanup on error
            if 'file_path' in locals():
                try:
                    await aiofiles.os.remove(file_path)
                except:
                    pass
            raise Exception(f"Error saving document: {str(e)}")

    async def get_document(self, filename: str) -> Optional[DocumentInfo]:
        """
        Get document information with async file operations
        """
        try:
            file_path = os.path.join(self.upload_dir, filename)
            if not await aiofiles.os.path.exists(file_path):
                return None

            # Get file stats asynchronously
            stats = await aiofiles.os.stat(file_path)

            # Extract document type from filename
            doc_type = filename.split('_')[0]
            try:
                document_type = DocumentType(doc_type)
            except ValueError:
                document_type = DocumentType.RESUME  # Default to resume if type is invalid

            return DocumentInfo(
                filename=filename,
                original_filename=filename,
                file_path=file_path,
                document_type=document_type,
                size=stats.st_size,
                content_type="application/octet-stream",  # Default content type
                last_modified=datetime.fromtimestamp(stats.st_mtime)
            )
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    async def delete_document(self, filename: str) -> bool:
        """
        Delete a document with async operations
        """
        try:
            file_path = os.path.join(self.upload_dir, filename)
            if await aiofiles.os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
                return True
            return False
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")

    async def list_documents(self, document_type: Optional[DocumentType] = None) -> DocumentListResponse:
        """
        List all documents with optional filtering by type
        """
        try:
            documents = []
            async for entry in aiofiles.os.scandir(self.upload_dir):
                if entry.is_file():
                    # Extract document type from filename
                    doc_type = entry.name.split('_')[0]
                    try:
                        file_doc_type = DocumentType(doc_type)
                        if document_type and file_doc_type != document_type:
                            continue
                    except ValueError:
                        continue  # Skip files with invalid document types

                    stats = await aiofiles.os.stat(entry.path)
                    documents.append(
                        DocumentInfo(
                            filename=entry.name,
                            original_filename=entry.name,
                            file_path=entry.path,
                            document_type=file_doc_type,
                            size=stats.st_size,
                            content_type="application/octet-stream",
                            last_modified=datetime.fromtimestamp(stats.st_mtime)
                        )
                    )
            return DocumentListResponse(
                documents=documents,
                total_count=len(documents),
                document_type=document_type
            )
        except Exception as e:
            raise Exception(f"Error listing documents: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)