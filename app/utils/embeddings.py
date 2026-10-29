from sentence_transformers import SentenceTransformer
import asyncio
from concurrent.futures import ThreadPoolExecutor

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384 dimensions
executor = ThreadPoolExecutor()

async def generate_embedding(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(
        executor,
        lambda: model.encode(text).tolist()
    )
    return embedding