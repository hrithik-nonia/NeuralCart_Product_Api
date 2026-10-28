import json
import os
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv
from app.database import products_collection
from bson import ObjectId

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


async def handle_order_placed(data: dict):
    """Stock kam karo jab order place ho"""
    product_id = data.get("items", {}).get("product_id")
    quantity = data.get("items", {}).get("quantity")

    if not product_id or not quantity:
        print("❌ Invalid event data:", data)
        return

    result = await products_collection.update_one(
        {
            "_id": ObjectId(product_id),
            "stock": {"$gte": quantity}  # stock enough hai?
        },
        {"$inc": {"stock": -quantity}}
    )

    if result.modified_count == 0:
        print(f"⚠️ Stock update failed for product: {product_id}")
    else:
        print(f"✅ Stock updated — product: {product_id}, reduced by: {quantity}")


async def handle_order_cancelled(data: dict):
    """Stock wapas karo jab order cancel ho"""
    product_id = data.get("items", {}).get("product_id")
    quantity = data.get("items", {}).get("quantity")

    if not product_id or not quantity:
        print("❌ Invalid event data:", data)
        return

    await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"stock": quantity}}  # stock wapas
    )
    print(f"✅ Stock restored — product: {product_id}, restored by: {quantity}")


# Topic → Handler mapping
HANDLERS = {
    "neuralmcart.order.placed": handle_order_placed,
    "neuralmcart.order.cancelled": handle_order_cancelled,
}


async def start_consumer():
    consumer = AIOKafkaConsumer(
        *HANDLERS.keys(),  # saare topics
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="product-service-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
    )

    await consumer.start()
    print("✅ Kafka consumer started — Product Service")

    try:
        async for message in consumer:
            topic = message.topic
            data = message.value
            print(f"📩 Event received → {topic}: {data}")

            handler = HANDLERS.get(topic)
            if handler:
                await handler(data)

    except Exception as e:
        print(f"❌ Consumer error: {e}")
    finally:
        await consumer.stop()
        print("🔴 Kafka consumer stopped")