from aiokafka import AIOKafkaProducer
import json
import os

producer = None

async def start_producer():
    global producer
    servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    producer = AIOKafkaProducer(bootstrap_servers=servers)
    await producer.start()
    print("✅ Kafka Producer started")

async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        print("🔴 Kafka Producer stopped")

async def publish_product_view(user_id: str, product_id: str):
    print(f"Publishing: user={user_id}, product={product_id}")
    if not producer:
        print("Producer is None!")
        return
    if not producer:
        return
    message = {
        "user_id": user_id,
        "product_id": product_id,
        "event_type": "view",
    }
    await producer.send(
        "product-views",
        value=json.dumps(message).encode("utf-8")
    )
    await producer.flush()