from fastapi import APIRouter, HTTPException, status, Request, UploadFile, File, Depends
from app.utils.cloudinary import upload_image
from app.utils.dependency import get_current_user
from app.utils.limiter import limiter
from app.utils.compress_image import compress_image


router = APIRouter(prefix="/upload", tags=["Upload Image APIs"])

MAX_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


# Upload Image End Point
@router.post("/image", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def upload_product_image(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
  # 1. Admin check
  if user.get("role") != "admin":
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Admin access required"
      )
      
  # Type check
  if file.content_type not in ALLOWED_TYPES:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Sirf JPEG, PNG, WEBP allowed hai",
      )
      
      
  # File bytes pado
  file_bytes = await file.read()
  
  # Size check
  if len(file_bytes) > MAX_SIZE:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="File size 5MB se zyada nahi honi chahiye",
      )
      
      
  # Empty file check
  if len(file_bytes) == 0:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Empty file nahi chalega",
      )
      
      
  # compressed image
  file_bytes = await compress_image(file_bytes)
      
  # Cloudinary pe upload
  url = await upload_image(file_bytes)
  
  return {"url": url}