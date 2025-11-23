from dataclasses import dataclass
from typing import Iterable, Tuple

from PIL import Image

Color = Tuple[int, int, int]


@dataclass
class SeatDetectionConfig:
    target_color: Color = (76, 175, 80)  # cinema green
    tolerance: int = 40
    min_blob_size: int = 10


def is_color_match(pixel: Color, target: Color, tolerance: int) -> bool:
    r, g, b = pixel
    return (
        abs(r - target[0]) <= tolerance
        and abs(g - target[1]) <= tolerance
        and abs(b - target[2]) <= tolerance
    )


def count_seats_from_image(
    image_path: str, config: SeatDetectionConfig | None = None
) -> Tuple[int, Iterable[int]]:
    """Return count of seat blobs and their sizes."""
    cfg = config or SeatDetectionConfig()
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    pixels = img.load()

    visited = set()
    blobs = 0
    sizes = []

    def flood_fill(x0: int, y0: int) -> int:
        stack = [(x0, y0)]
        size = 0
        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            size += 1
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited and is_color_match(
                        pixels[nx, ny], cfg.target_color, cfg.tolerance
                    ):
                        stack.append((nx, ny))
        return size

    for x in range(width):
        for y in range(height):
            if (x, y) in visited:
                continue
            if not is_color_match(pixels[x, y], cfg.target_color, cfg.tolerance):
                continue
            blob_size = flood_fill(x, y)
            if blob_size >= cfg.min_blob_size:
                blobs += 1
                sizes.append(blob_size)

    return blobs, sizes
