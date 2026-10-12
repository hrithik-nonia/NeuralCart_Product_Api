from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

# class CategoryUpdate(BaseModel):
#     name: Optional[str] = None
#     slug: Optional[str] = None
#     description: Optional[str] = None
#     icon: Optional[str] = None
#     is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime