from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import client, categories_collection
from app.utils.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.redis import shared_redis
from app.routes.categories import router as category_router
from app.routes.products import router as product_router
from app.routes.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MongoDB check
    await client.admin.command("ping")
    print("✅ MongoDB connected")
    
    await shared_redis.ping()       # ← add karo
    print("✅ Redis connected")

    # Indexes
    await categories_collection.create_index("slug", unique=True)
    print("✅ Indexes created")

    yield

    client.close()
    print("🔴 MongoDB disconnected")


app = FastAPI(
    title="Product API",
    description="Product service for NeuralCart",
    version="1.0.0",
    docs_url="/product-apis",
    lifespan=lifespan
)

# limiter configure kiya
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.include_router(product_router)
app.include_router(category_router)
app.include_router(upload_router)


@app.get("/health")
async def health():
    return {"message": "Product Service Running"}