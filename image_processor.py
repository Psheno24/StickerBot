from io import BytesIO

from PIL import Image
from rembg import remove


MAX_SIZE_KB = 512
TARGET_SIZE = (512, 512)


def _fit_on_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale image to fit inside size, centered on transparent canvas."""
    image = image.convert("RGBA")
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))

    ratio = min(size[0] / image.width, size[1] / image.height)
    new_width = max(1, int(image.width * ratio))
    new_height = max(1, int(image.height * ratio))
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    offset_x = (size[0] - new_width) // 2
    offset_y = (size[1] - new_height) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    return canvas


def _save_webp_under_limit(image: Image.Image, max_bytes: int) -> bytes:
    """Save as WEBP, lowering quality until under max_bytes."""
    for quality in range(95, 29, -5):
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=quality, method=6)
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            return data

    # Last resort: slightly smaller canvas then retry
    smaller = _fit_on_canvas(image, (480, 480))
    final_canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
    final_canvas.paste(smaller, (16, 16), smaller)

    for quality in range(85, 29, -5):
        buffer = BytesIO()
        final_canvas.save(buffer, format="WEBP", quality=quality, method=6)
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            return data

    raise ValueError(f"Не удалось сжать изображение до {max_bytes // 1024} КБ")


def process_sticker_image(image_bytes: bytes) -> bytes:
    """
    Remove background, resize to 512x512, export as WEBP under 512 KB.
    """
    no_bg = remove(image_bytes)
    image = Image.open(BytesIO(no_bg)).convert("RGBA")
    sticker = _fit_on_canvas(image, TARGET_SIZE)

    if sticker.width != 512 or sticker.height != 512:
        sticker = sticker.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

    return _save_webp_under_limit(sticker, MAX_SIZE_KB * 1024)
