from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    images: list[HttpUrl] = []
    category_id: str
    is_active: bool = True
    
class CategoryInfo(BaseModel):
    id: str
    name: str


class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    images: list[str] = []
    category: Optional[CategoryInfo] = None
    is_active: bool
    created_at: datetime
    
class UpdateProduct(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    images: Optional[list[HttpUrl]] = None
    category_id: Optional[str] = None
    is_active: Optional[bool] = None