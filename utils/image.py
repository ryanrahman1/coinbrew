from PIL import Image
from io import BytesIO
import uuid

def process_image(file_bytes: bytes, max_size=(500,500)) -> BytesIO:
    img = Image.open(BytesIO(file_bytes))
    img.thumbnail(max_size, Image.LANCZOS)

    output = BytesIO()
    if img.format == "PNG":
        img.save(output, format="PNG", optimize=True)
    else:
        img.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)
    return output

def generate_filename(symbol: str, ext: str = "png") -> str:
    return f"{symbol}_{uuid.uuid4().hex}.{ext}"