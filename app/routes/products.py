from fastapi import APIRouter, status, HTTPException, Request, Depends
from app.utils.limiter import limiter
from app.utils.dependency import get_current_user


router = APIRouter(prefix="/product", tags=["Product APIs"],)


# Create Produuct
# @router.post("/create-Product", status_code= status.HTTP_200_OK)
# @limiter.limit("5/minute")
# async def create_product(request: Request, current_user: dict = Depends(get_current_user))


