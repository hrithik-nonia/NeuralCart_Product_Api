from fastapi import APIRouter, HTTPException, Request, Depends, status, Query
from app.utils.limiter import limiter
from app.models.category import CategoryCreate, CategoryResponse, CategoryUpdate, CategoryDeleteResponse
from app.utils.dependency import get_current_user
from app.database import categories_collection
from datetime import datetime, timezone
from typing import Optional
from app.redis import shared_redis
import json
from bson import ObjectId


router = APIRouter(prefix="/category", tags=["Category APIs"],)


# Create Category
@router.post("/create", status_code= status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_category(request: Request, category_data: CategoryCreate, user: dict = Depends(get_current_user))-> CategoryResponse:
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
@router.get("/all", status_code= status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_categories(request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    )-> dict | None:
  # Claculate Skip
  skip = (page - 1) * limit
  
  # Cache key banao
  cache_key = f"categories:page={page}:limit={limit}:is_active={is_active}"
  
  # Redis check karo
  cached = await shared_redis.get(cache_key)
  if cached:
    return json.loads(cached)
  
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

  # Datas
  categories = result["data"]
  total = result["total"][0]["count"] if result["total"] else 0
  
  result= {
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
  
  # Redis mein save karo — 5 min TTL
  await shared_redis.setex(cache_key, 10 * 60, json.dumps(result, default=str))
  
  return result


# Get Category
@router.get("/{category_id}", status_code= status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_category(request: Request, category_id: str)-> CategoryResponse:
  # Redis Key Banao
  cache_key = f"category:{category_id}"
  
  # 1. Redis cache check
  cached = await shared_redis.get(cache_key)
  if cached:
    return CategoryResponse(**json.loads(cached))
  
  # 2. Valid ObjectId check
  try:
    obj_id = ObjectId(category_id)
  except Exception:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid category id"
    )
    
  # 3. DB se fetch
  category = await categories_collection.find_one({"_id": obj_id})
  if not category:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Category nahi mili"
    )
    
  # 4. Response banao
  result = CategoryResponse(
    id=str(category["_id"]),
    name=category["name"],
    slug=category["slug"],
    description=category.get("description"),
    is_active=category["is_active"],
    created_at=category["created_at"]
  )
  
  # 5. Redis mein cache karo
  await shared_redis.setex(
    f"category:{category_id}",
    15 * 60,  # 1 hour
    json.dumps(result.model_dump(), default=str)
  )
  return result


# Edit Category
@router.patch("/{category_id}", status_code= status.HTTP_200_OK)
@limiter.limit("5/minute")
async def edit_category(request: Request, category_id: str, category_data: CategoryUpdate, user: dict = Depends(get_current_user))-> CategoryResponse:
  # 1. Admin check
  if user.get("role") != "admin":
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Admin access required"
      )
    
  # 2. Validate ID
  try:
      obj_id = ObjectId(category_id)
  except Exception:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Invalid category ID"
      )
    
  # 3. Only supplied fields
  update_data = category_data.model_dump(exclude_unset=True)

  if not update_data:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="At least one field is required"
      )
      
  # 4. Fetch category once
  category = await categories_collection.find_one({"_id": obj_id})

  if not category:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Category not found"
      )
      
  # 5. Prepare update
  if "name" in update_data:
      name = update_data["name"].strip()

      if not name:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Category name cannot be empty"
          )

      update_data["name"] = name.title()
      update_data["slug"] = name.lower().replace(" ", "-")

    
  # 6. Update MongoDB
  await categories_collection.update_one(
      {"_id": obj_id},
      {"$set": update_data}
  )

  # 7. Update local object; no second DB query
  category.update(update_data)
      
  # 8. Clear Redis cache
  await shared_redis.delete(f"category:{category_id}")

  # 9. Return response from local data
  return CategoryResponse(
      id=str(category["_id"]),
      name=category["name"],
      slug=category["slug"],
      description=category.get("description"),
      is_active=category["is_active"],
      created_at=category["created_at"]
  )


# Delete Category
@router.delete("/{category_id}", status_code= status.HTTP_200_OK)
@limiter.limit("5/minute")
async def delete_category(request: Request, category_id: str, user: dict = Depends(get_current_user))-> CategoryDeleteResponse:
  # 1. Admin check
  if user.get("role") != "admin":
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Admin access required"
      )
    
  # 2. Validate ID
  try:
      obj_id = ObjectId(category_id)
  except Exception:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Invalid category ID"
      )
      
  # 3. Fetch category once
  category = await categories_collection.find_one(
    {"_id": obj_id},
    {"name": 1},
    )
  
  if not category:
    raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Category Not Found")
  
  # 4. Delete from MongoDB
  await categories_collection.delete_one(
      {"_id": obj_id}
  )
  
  # 5. Delete Redis cache
  await shared_redis.delete(f"category:{category_id}")
  
  # 6. Return response
  return CategoryDeleteResponse(
    message="Category deleted successfully",
    name=category["name"]
  )
  
  