from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter
from rembg import remove


MAX_SIZE_KB = 512
TARGET_SIZE = (512, 512)


def _has_green_background(image: Image.Image, sample_size: int = 50) -> bool:
    """Detect if the image has a green-screen style background by sampling corners."""
    arr = np.array(image.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    corners = np.concatenate([
        arr[:sample_size, :sample_size].reshape(-1, 3),
        arr[:sample_size, -sample_size:].reshape(-1, 3),
        arr[-sample_size:, :sample_size].reshape(-1, 3),
        arr[-sample_size:, -sample_size:].reshape(-1, 3),
    ])
    r, g, b = corners[:, 0], corners[:, 1], corners[:, 2]
    green_pixels = (g > r + 20) & (g > b + 20) & (g > 80)
    return green_pixels.mean() > 0.4


def _chroma_key_remove(image: Image.Image) -> Image.Image:
    """Remove green background using HSV color-based chroma keying."""
    arr = np.array(image.convert("RGBA"), dtype=np.float32)
    rgb = arr[:, :, :3]

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c + 1e-10

    # Compute hue (0-360) and saturation (0-1)
    hue = np.zeros_like(r)
    mask_g = (max_c == g) & (delta > 1)
    mask_r = (max_c == r) & (delta > 1)
    mask_b = (max_c == b) & (delta > 1)
    hue[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
    hue[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2)
    hue[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4)

    sat = delta / (max_c + 1e-10)

    # Green hue range: 60-170 degrees, saturation > 0.2, brightness > 50
    is_green = (hue > 60) & (hue < 170) & (sat > 0.2) & (max_c > 50)

    # Soft edge: transition zone
    green_strength = np.zeros_like(r)
    core_green = is_green & (sat > 0.4) & (g > r + 40) & (g > b + 40)
    edge_green = is_green & ~core_green

    green_strength[core_green] = 1.0
    green_strength[edge_green] = np.clip(sat[edge_green] * 1.5 - 0.3, 0, 1)

    # Apply alpha based on green strength
    alpha = arr[:, :, 3]
    alpha = alpha * (1.0 - green_strength)

    # Despill: reduce green channel on edge pixels
    spill_mask = (green_strength > 0) & (green_strength < 1.0)
    avg_rb = (r + b) / 2.0
    arr[spill_mask, 1] = np.minimum(g[spill_mask], avg_rb[spill_mask] + 10)

    arr[:, :, 3] = alpha
    result = Image.fromarray(arr.astype(np.uint8), "RGBA")

    # Slight erode on alpha to clean edges
    alpha_channel = result.split()[3]
    alpha_channel = alpha_channel.filter(ImageFilter.MinFilter(3))
    result.putalpha(alpha_channel)

    return result


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
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")

    if _has_green_background(image):
        image = _chroma_key_remove(image)
    else:
        no_bg = remove(image_bytes)
        image = Image.open(BytesIO(no_bg)).convert("RGBA")

    # Sharpen after downscale to preserve detail
    sticker = _fit_on_canvas(image, TARGET_SIZE)
    sticker = sticker.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=2))

    return _save_webp_under_limit(sticker, MAX_SIZE_KB * 1024)
