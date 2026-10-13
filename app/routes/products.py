from fastapi import APIRouter, status, HTTPException, Request, Depends, Query
from app.utils.limiter import limiter
from app.utils.dependency import get_current_user
from app.models.product_model import ProductCreate, ProductResponse, CategoryInfo, UpdateProduct
from app.database import products_collection, categories_collection
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from app.redis import shared_redis
import json
from typing import Optional

router = APIRouter(prefix="/product", tags=["Product APIs"])


# Create Product
@router.post("/create-product", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_product(
    request: Request,
    product_data: ProductCreate,
    user: dict = Depends(get_current_user)
) -> dict | None:

    # 1. Admin check
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # 2. Data clean karo — strip spaces
    name = product_data.name.strip()
    description = product_data.description.strip() if product_data.description else None

    # 3. Category exist karti hai?
    try:
      category_object_id = ObjectId(product_data.category_id)
    except InvalidId:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Invalid category_id"
      )

    # Pehle Redis check karo
    cached_category = await shared_redis.get(f"category:{product_data.category_id}")
    if cached_category:
        category = json.loads(cached_category)
    else:
        # Cache miss — DB se lo
        category = await categories_collection.find_one(
            {"_id": category_object_id, "is_active": True},
            {"_id": 1}
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category nahi mili ya inactive hai"
            )
        # Redis mein save karo
        await shared_redis.setex(
            f"category:{product_data.category_id}",
            15 * 60,
            json.dumps(category, default=str)
        )

    # 4. User id nikalo
    created_by = user.get("id")

    # 5. DB mein save karo
    new_product = {
        "name": name,
        "description": description,
        "price": product_data.price,
        "stock": product_data.stock,
        "images": [str(img) for img in product_data.images],
        "category_id": ObjectId(product_data.category_id),
        "is_active": product_data.is_active,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc),
    }

    result = await products_collection.insert_one(new_product)

    return {
        "id": str(result.inserted_id),
        "message": "Product create ho gaya"
    }
    
    
# Get Products
@router.get("/products", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def products(request: Request, 
  page: int = Query(default=1, ge=1), 
  limit: int = Query(default=10, ge=1, le=100),
  is_active: Optional[bool] = Query(default=None),
  category_id: Optional[str] = Query(default=None),)-> dict | None:
  # Claculate Skip
  skip = (page - 1) * limit
  
  # Cache key banao
  cache_key = f"products:page={page}:limit={limit}:is_active={is_active}:category={category_id}"
  
  # Redis check karo
  cached = await shared_redis.get(cache_key)
  if cached:
    return json.loads(cached)
  
  # Filter banao
  query = {}
  if is_active is not None:
    query["is_active"] = is_active

  if category_id:
    try:
        query["category_id"] = ObjectId(category_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid category_id")
    
  # Pipeline banao
  pipeline = [
      {"$match": query},
      {"$sort": {"created_at": -1}},
      {"$facet": {
          "data": [
              {"$skip": skip},
              {"$limit": limit},
              # Category join karo
              {"$lookup": {
                  "from": "categories",
                  "localField": "category_id",
                  "foreignField": "_id",
                  "as": "category",
                  "pipeline": [
                      {"$project": {"_id": 0, "id": {"$toString": "$_id"}, "name": 1}}
                  ]
              }},
              {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
              # Projection
              {"$project": {
                  "_id": 0,
                  "id": {"$toString": "$_id"},
                  "name": 1,
                  "description": 1,
                  "price": 1,
                  "stock": 1,
                  "images": 1,
                  "category": 1,
                  "is_active": 1,
                  "created_at": 1,
              }}
          ],
          "total": [
              {"$count": "count"}
          ]
      }}
  ]
  
  result = await products_collection.aggregate(pipeline).to_list(length=1)
  result = result[0] if result else {"data": [], "total": []}
  
  products_list = result["data"]
  total = result["total"][0]["count"] if result["total"] else 0
  
  response_data = {
      "data": products_list,
      "pagination": {
          "page": page,
          "limit": limit,
          "total": total,
          "total_pages": -(-total // limit),
          "has_next": (page * limit) < total,
          "has_prev": page > 1,
      }
  }

  # Redis mein save karo
  await shared_redis.setex(
      cache_key,
      10 * 60,
      json.dumps(response_data, default=str)
  )

  return response_data


# Get Product By Id
@router.get("/products/{product_id}", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def get_product_by_id(request: Request, product_id: str) -> ProductResponse:
    
    # 1. Cache key
    cache_key = f"product:{product_id}"
    
    # 2. Redis check
    cached = await shared_redis.get(cache_key)
    if cached:
        return ProductResponse(**json.loads(cached))
    
    # 3. Valid ObjectId check
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )
        
        
    # 4. Single DB query using aggregation pipeline
    pipeline = [
        {"$match": {"_id": obj_id}},
        {
            "$lookup": {
                "from": "categories",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }
        },
        {
            "$unwind": {
                "path": "$category",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "price": 1,
                "stock": 1,
                "image": 1,
                "is_active": 1,
                "created_at": 1,
                "category._id": 1,
                "category.name": 1
            }
        }
    ]
    
    result = await products_collection.aggregate(pipeline).to_list(length=1)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product nahi mila"
        )

    product = result[0]
    category = product.get("category")
    
    # 5. Response
    response = ProductResponse(
        id=str(product["_id"]),
        name=product["name"],
        description=product.get("description"),
        price=product["price"],
        stock=product["stock"],
        images=[product["image"]] if product.get("image") else [],
        category=CategoryInfo(
            id=str(category["_id"]),
            name=category["name"]
        ) if category else None,
        is_active=product["is_active"],
        created_at=product["created_at"]
    )

    # 6. Redis cache — 1 hour
    await shared_redis.setex(
        cache_key,
        3600,
        response.model_dump_json()
    )

    return response
    

# Edit Product
@router.patch("/products/{product_id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def edit_product(
    request: Request,
    product_id: str,
    product_data: UpdateProduct,
    user: dict = Depends(get_current_user)
) -> dict | None:

    # 1. Admin check
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # 2. Incoming data check
    update_data = product_data.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kuch bhi update karne ke liye bhejo"
        )

    # 3. Valid ObjectId check
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )

    # 4. String fields strip karo
    if "name" in update_data:
        update_data["name"] = update_data["name"].strip()
    if "description" in update_data:
        update_data["description"] = update_data["description"].strip()

    # 5. images HttpUrl → string convert karo
    if "images" in update_data:
        update_data["images"] = [str(img) for img in update_data["images"]]

    # 6. category_id validate karo agar aa raha hai
    if "category_id" in update_data:
        try:
            cat_obj_id = ObjectId(update_data["category_id"])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id"
            )
        # Redis se check karo
        cached_cat = await shared_redis.get(f"category:{update_data['category_id']}")
        if not cached_cat:
            category = await categories_collection.find_one(
                {"_id": cat_obj_id, "is_active": True},
                {"_id": 1}
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category nahi mili ya inactive hai"
                )
        update_data["category_id"] = cat_obj_id

    # 7. DB update karo
    result = await products_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product nahi mila"
        )

    # 8. Cache invalidate karo
    await shared_redis.delete(f"product:{product_id}")
    async for key in shared_redis.scan_iter("products:*"):
        await shared_redis.delete(key)

    return {"message": "Product updated Successfully"}


# Delete Product
@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_product(
    request: Request,
    product_id: str,
    user: dict = Depends(get_current_user)
)-> None:
    # 1. Admin check
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # 2. Valid ObjectId check
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )

    # 3. DB se delete karo
    result = await products_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product nahi mila"
        )

    # 4. Cache invalidate karo
    await shared_redis.delete(f"product:{product_id}")
    async for key in shared_redis.scan_iter("products:*"):
        await shared_redis.delete(key)
        
        
        