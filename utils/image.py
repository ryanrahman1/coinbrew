from PIL import Image
from io import BytesIO
import uuid

def generate_filename(symbol: str, ext: str) -> str:
    # Use a uuid to avoid collisions; symbols are upper/lower-insensitive in storage paths
    unique_id = uuid.uuid4().hex
    safe_symbol = symbol.strip().upper()
    return f"{safe_symbol}-{unique_id}.{ext}"

def process_image(file_bytes: bytes, max_size=(500,500)) -> bytes:
    img = Image.open(BytesIO(file_bytes))
    img.thumbnail(max_size, Image.LANCZOS)

    output = BytesIO()
    if img.format == "PNG":
        img.save(output, format="PNG", optimize=True)
    else:
        img.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)
    
    return output.getvalue()
