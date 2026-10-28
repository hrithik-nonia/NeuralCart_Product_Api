import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

executor = ThreadPoolExecutor()

async def upload_image(file_bytes: bytes, folder: str = "neuralcart/products") -> str:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        lambda: cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            allowed_formats=["jpg", "jpeg", "png", "webp"],
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
    )
    return result["secure_url"]