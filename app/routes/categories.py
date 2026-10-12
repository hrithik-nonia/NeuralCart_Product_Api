from fastapi import APIRouter, HTTPException, Request, Depends, status
from app.utils.limiter import limiter
from app.models.category import CategoryCreate


router = APIRouter(prefix="/category", tags=["Category APIs"],)


# Create Category
@router.post("/categories", status_code= status.HTTP_200_OK)
@limiter.limit("5/minute")
async def create_category(request: Request, category_data: CategoryCreate):
  return "create category"


# Get Categories
@router.get("/categories", status_code= status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_categories(request: Request):
  return "get all cat"


# Get Category
@router.get("/categories/{id}", status_code= status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_category(request: Request):
  return "get category"


# Edit Category
@router.patch("/categories/{id}", status_code= status.HTTP_200_OK)
@limiter.limit("5/minute")
async def edit_category(request: Request):
  return "edit cat"


# Delete Category
@router.delete("/categories/{id}", status_code= status.HTTP_200_OK)
@limiter.limit("5/minute")
async def delete_category(request: Request):
  return "delete cat"