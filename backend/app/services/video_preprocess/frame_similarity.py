from io import BytesIO
from pathlib import Path

from PIL import Image

from app.storage.local_store import data_url_to_bytes


def difference_hash(image: Image.Image) -> str:
    grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(grayscale.getdata())
    value = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            value = (value << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
    return f"{value:016x}"


def difference_hash_path(path: Path) -> str:
    with Image.open(path) as image:
        return difference_hash(image)


def difference_hash_data_url(data_url: str) -> str:
    with Image.open(BytesIO(data_url_to_bytes(data_url))) as image:
        return difference_hash(image)


def hash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()
