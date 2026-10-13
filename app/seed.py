# seed.py — root ya product-service folder mein banao
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import random
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DATABASE_NAME")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Sample data
CATEGORIES = []  # neeche fill hongi
NAMES = ["Premium", "Classic", "Ultra", "Pro", "Elite", "Basic", "Smart", "Eco"]
PRODUCTS = ["Shirt", "Laptop", "Phone", "Watch", "Shoes", "Bag", "Camera", "Chair"]
BRANDS = ["Nike", "Apple", "Samsung", "Sony", "Puma", "Dell", "HP", "LG"]

BATCH_SIZE = 1000  # ek baar mein 1000 insert
TOTAL = 1000000


async def get_categories():
    cats = await db.categories.find({}, {"_id": 1}).to_list(length=100)
    return [cat["_id"] for cat in cats]


def make_product(category_ids: list) -> dict:
    name = f"{random.choice(NAMES)} {random.choice(BRANDS)} {random.choice(PRODUCTS)}"
    return {
        "name": name,
        "description": f"{name} - high quality product",
        "price": round(random.uniform(10.0, 9999.0), 2),
        "stock": random.randint(0, 500),
        "images": [
            f"https://res.cloudinary.com/demo/image/upload/sample{random.randint(1,10)}.jpg"
        ],
        "category_id": random.choice(category_ids),
        "is_active": random.choice([True, True, True, False]),  # 75% active
        "created_at": datetime.now(timezone.utc),
    }


async def seed():
    print("🚀 Seeding start...")

    category_ids = await get_categories()
    if not category_ids:
        print("❌ Pehle categories banao DB mein")
        return

    inserted = 0
    batch_num = 0

    while inserted < TOTAL:
        batch_size = min(BATCH_SIZE, TOTAL - inserted)
        batch = [make_product(category_ids) for _ in range(batch_size)]

        await db.products.insert_many(batch, ordered=False)

        inserted += batch_size
        batch_num += 1

        if batch_num % 10 == 0:
            print(f"✅ {inserted:,} / {TOTAL:,} inserted")

    print(f"🎉 Done! {inserted:,} products inserted")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())