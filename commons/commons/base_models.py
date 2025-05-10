import hashlib
import logging
from datetime import datetime
from typing import Generic, TypeVar, Dict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

I = TypeVar('I')  # Type variable for ID
U = TypeVar('U')  # Type variable for User ID
D = TypeVar('D')  # Type variable for Object data


class BaseSchema(BaseModel, Generic[I, U]):
    """Base schema class for all models with ID and creation tracking."""
    id: I | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    created_by: U | None = Field(default=None, alias="createdBy")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UpdatableSchema(BaseModel, Generic[I, U]):
    """Base schema class for models that can be updated."""
    id: I | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    created_by: U | None = Field(default=None, alias="createdBy")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    updated_by: U | None = Field(default=None, alias="updatedBy")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ObjectWithUniqueID(BaseModel, Generic[D]):
    """Schema for objects that require unique identification"""
    unique_id: str | None = Field(default=None, alias="uniqueId")
    object: D
    headers: Dict[str, str] | None = None

    def get_unique_id(self) -> str:
        """Generate or return the unique ID for the object"""
        if self.unique_id is not None:
            return self.unique_id

        try:
            # Create MD5 hash of the object's string representation
            md5_hash = hashlib.md5(str(self.object).encode()).hexdigest()
            self.unique_id = f'"{md5_hash}"'
        except Exception as ex:
            logger.error(f"Error while generating unique id for object: {str(self.object)[:500]}", exc_info=ex)
            self.unique_id = f'"{hash(str(self.object)):x}"'

        return self.unique_id

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
