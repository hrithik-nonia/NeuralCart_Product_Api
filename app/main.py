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
import asyncio
from app.kafka.consumer import start_consumer
from app.kafka.producer import start_producer, stop_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MongoDB check
    await client.admin.command("ping")
    print("✅ MongoDB connected")
    
    await shared_redis.ping()       # ← add karo
    print("✅ Redis connected")
    
    # Kafka consumer background mein chalao
    consumer_task = asyncio.create_task(start_consumer())
    print("✅ Kafka consumer started")

    # Indexes
    await categories_collection.create_index("slug", unique=True)
    print("✅ Indexes created")
    
    # Kafka producer start karo
    await start_producer()
    print("✅ Kafka producer started")

    yield

    await stop_producer()
    consumer_task.cancel()
    client.close()
    print("🔴 MongoDB disconnected")
    print("🔴 Redis disconnected")
    print("🔴 Kafka consumer stopped")
    print("🔴 Kafka producer stopped")


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