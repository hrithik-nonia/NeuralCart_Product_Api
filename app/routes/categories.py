from fastapi import APIRouter, HTTPException, Request, Depends, status, Query
from app.utils.limiter import limiter
from app.models.category import CategoryCreate, CategoryResponse
from app.utils.dependency import get_current_user
from app.database import categories_collection
from datetime import datetime, timezone
from typing import Optional


router = APIRouter(prefix="/category", tags=["Category APIs"],)


# Create Category
@router.post("/categories", status_code= status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_category(request: Request, category_data: CategoryCreate, user= Depends(get_current_user))-> CategoryResponse:
  # Cheak, Only Admin Allow
  if user.get("role") != "admin":
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Admin access required"
    )
    
  # generate slug/name
  slug = category_data.name.strip().lower().replace(" ", "-")
  name = category_data.name.title()
    
  # Cheak, Data In DB
  existing_category = await categories_collection.find_one(
        {"slug": slug},
        {"_id": 1}
    )
  if existing_category:
    raise HTTPException(
      status_code= status.HTTP_409_CONFLICT,
      detail="Category Already Exist"
    )
    
  # Category Data
  category = {
      "name": name,
      "slug": slug,
      "description": category_data.description,
      "is_active": category_data.is_active,
      "created_at": datetime.now(timezone.utc)
    }
  
  # DB Indertion
  result = await categories_collection.insert_one(category)

  return CategoryResponse(
      id=str(result.inserted_id),
      name=name,
      slug=slug,
      description=category.get("description"),
      is_active=category["is_active"],
      created_at=category["created_at"]
    )


# Get Categories
@router.get("/categories", status_code= status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_categories(request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    ):
  # Claculate Skip
  skip = (page - 1) * limit
  
  # Filter banao
  query = {}
  if is_active is not None:
    query["is_active"] = is_active
    
  # Create Pipeline To Get Tolal Count And Data
  pipeline = [
      {"$match": query},
      {"$sort": {"created_at": -1}},
      {"$facet": {
          "data": [
              {"$skip": skip},
              {"$limit": limit},
              {"$project": {
                  "id": {"$toString": "$_id"},
                  "name": 1,
                  "slug": 1,
                  "description": 1,
                  "is_active": 1,
                  "created_at": 1,
              }}
          ],
          "total": [
              {"$count": "count"}
          ]
      }}
  ]

  # Query Run
  result = await categories_collection.aggregate(pipeline).to_list(length=1)
  result = result[0] if result else {"data": [], "total": []}

  # 
  categories = result["data"]
  total = result["total"][0]["count"] if result["total"] else 0
  
  return {
    "data": [
      CategoryResponse(
        id=cat["id"],
        name=cat["name"],
        slug=cat["slug"],
        description=cat.get("description"),
        is_active=cat["is_active"],
        created_at=cat["created_at"],
      )
      for cat in categories
    ],
    "pagination": {
      "page": page,
      "limit": limit,
      "total": total,
      "total_pages": -(-total // limit),
      "has_next": (page * limit) < total,
      "has_prev": page > 1,
    }
  }


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