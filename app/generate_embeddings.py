import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DATABASE_NAME")]
products_collection = db["products"]

model = SentenceTransformer("all-MiniLM-L6-v2")

BATCH_SIZE = 100

async def generate_embeddings():
    print("🚀 Start...")
    
    total = await products_collection.count_documents({"embedding": {"$exists": False}})
    print(f"Total products without embedding: {total}")
    
    processed = 0
    cursor = products_collection.find(
        {"embedding": {"$exists": False}},
        {"_id": 1, "name": 1, "description": 1}
    ).batch_size(BATCH_SIZE)
    
    batch = []
    async for product in cursor:
        batch.append(product)
        
        if len(batch) == BATCH_SIZE:
            await process_batch(batch)
            processed += len(batch)
            print(f"✅ {processed}/{total} done")
            batch = []
    
    # Last batch
    if batch:
        await process_batch(batch)
        processed += len(batch)
    
    print(f"🎉 Done! {processed} embeddings generated")
    client.close()


async def process_batch(batch: list):
    texts = [
        f"{p['name']} {p.get('description', '')}"
        for p in batch
    ]
    
    # Batch mein embeddings generate karo — fast hoga
    embeddings = model.encode(texts, batch_size=32).tolist()
    
    # Bulk update
    from pymongo import UpdateOne
    from motor.motor_asyncio import AsyncIOMotorClient
    
    ops = [
        UpdateOne(
            {"_id": p["_id"]},
            {"$set": {"embedding": emb}}
        )
        for p, emb in zip(batch, embeddings)
    ]
    
    await products_collection.bulk_write(ops)


if __name__ == "__main__":
    asyncio.run(generate_embeddings())