from PIL import Image
import io

async def compress_image(file_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(file_bytes))
    
    # Max 1200px width
    if img.width > 1200:
        ratio = 1200 / img.width
        new_size = (1200, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format="WEBP", quality=85)
    return output.getvalue()