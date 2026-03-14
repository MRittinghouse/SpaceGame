"""Pixel art asset processing pipeline.

PIL-based functions for downscaling, palette quantization, alpha cleanup,
outline enforcement, sprite sheet packing/unpacking, and palette swapping.
Framework-agnostic — no pygame dependency.
"""

from collections import deque

from PIL import Image, ImageChops


def remove_background(
    img: Image.Image,
    tolerance: int = 40,
) -> Image.Image:
    """Remove background using green-screen keying with flood fill.

    Detects bright green (#00FF00-ish) pixels used as chroma key background
    in AI-generated sprites. Also flood-fills from edges to catch any
    solid-color backgrounds. Sets matched pixels to transparent.

    Args:
        img: Source RGBA image.
        tolerance: Max color distance for edge flood fill.

    Returns:
        New image with background pixels set to transparent.
    """
    result = img.copy()
    pixels = result.load()
    width, height = result.size

    # Pass 1: Green-screen keying (catches all bright green pixels)
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if g > 150 and g > r + 50 and g > b + 50:
                pixels[x, y] = (0, 0, 0, 0)

    # Pass 2: Flood fill from edges to catch remaining background
    corners = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    bg_colors = [(c[0], c[1], c[2]) for c in corners if c[3] > 0]

    if not bg_colors:
        return result  # All corners already transparent — done

    def is_bg(r: int, g: int, b: int, a: int) -> bool:
        if a == 0:
            return True
        for bg in bg_colors:
            dist = (r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2
            if dist <= tolerance ** 2:
                return True
        return False

    visited = [[False] * height for _ in range(width)]
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in [0, height - 1]:
            r, g, b, a = pixels[x, y]
            if is_bg(r, g, b, a):
                queue.append((x, y))
                visited[x][y] = True
    for y in range(height):
        for x in [0, width - 1]:
            if not visited[x][y]:
                r, g, b, a = pixels[x, y]
                if is_bg(r, g, b, a):
                    queue.append((x, y))
                    visited[x][y] = True

    while queue:
        x, y = queue.popleft()
        pixels[x, y] = (0, 0, 0, 0)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not visited[nx][ny]:
                visited[nx][ny] = True
                r, g, b, a = pixels[nx, ny]
                if is_bg(r, g, b, a):
                    queue.append((nx, ny))

    return result


def resize_nearest(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize an image using nearest-neighbor interpolation.

    Preserves hard pixel edges with no anti-aliasing or blending.

    Args:
        img: Source RGBA image.
        size: Target (width, height).

    Returns:
        Resized image.
    """
    return img.resize(size, Image.NEAREST)


def _color_distance_sq(
    c1: tuple[int, int, int], c2: tuple[int, int, int]
) -> int:
    """Euclidean distance squared between two RGB colors."""
    return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2


def _nearest_color(
    color: tuple[int, int, int],
    palette: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """Find nearest palette color by RGB distance."""
    best = palette[0]
    best_dist = _color_distance_sq(color, best)
    for entry in palette[1:]:
        dist = _color_distance_sq(color, entry)
        if dist < best_dist:
            best = entry
            best_dist = dist
    return best


def quantize_to_palette(
    img: Image.Image,
    palette: list[tuple[int, int, int]],
) -> Image.Image:
    """Map every opaque pixel to the nearest color in a defined palette.

    Transparent pixels (alpha=0) are left unchanged.

    Args:
        img: Source RGBA image.
        palette: List of (R, G, B) colors to quantize to.

    Returns:
        New image with all opaque pixels mapped to palette colors.

    Raises:
        ValueError: If palette is empty.
    """
    if not palette:
        raise ValueError("Palette must not be empty.")

    result = img.copy()
    pixels = result.load()
    width, height = result.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            nearest = _nearest_color((r, g, b), palette)
            pixels[x, y] = (nearest[0], nearest[1], nearest[2], a)

    return result


def clean_alpha(
    img: Image.Image,
    threshold: int = 128,
) -> Image.Image:
    """Enforce binary alpha: fully opaque or fully transparent.

    Pixels with alpha >= threshold become 255, others become 0.
    RGB channels are preserved.

    Args:
        img: Source RGBA image.
        threshold: Alpha cutoff value. Defaults to 128.

    Returns:
        New image with binary alpha.
    """
    result = img.copy()
    pixels = result.load()
    width, height = result.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            new_a = 255 if a >= threshold else 0
            pixels[x, y] = (r, g, b, new_a)

    return result


def enforce_outline(
    img: Image.Image,
    outline_color: tuple[int, int, int],
) -> Image.Image:
    """Add 1px dark outline around non-transparent pixels.

    Transparent pixels adjacent (cardinal directions) to opaque pixels
    are filled with the outline color. Original opaque pixels are preserved.

    Args:
        img: Source RGBA image.
        outline_color: (R, G, B) color for the outline.

    Returns:
        New image with outline applied.
    """
    result = img.copy()
    pixels = result.load()
    src_pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            # Only consider transparent pixels as candidates for outline
            if src_pixels[x, y][3] > 0:
                continue

            # Check cardinal neighbors for opaque pixels
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if src_pixels[nx, ny][3] > 0:
                        pixels[x, y] = (
                            outline_color[0],
                            outline_color[1],
                            outline_color[2],
                            255,
                        )
                        break

    return result


def pack_sheet(frames: list[Image.Image]) -> Image.Image:
    """Pack multiple frame images into a horizontal strip.

    Args:
        frames: List of RGBA images (must all be same dimensions).

    Returns:
        Horizontal strip image.

    Raises:
        ValueError: If frames list is empty.
    """
    if not frames:
        raise ValueError("Frames list must not be empty.")

    frame_width, frame_height = frames[0].size
    sheet = Image.new("RGBA", (frame_width * len(frames), frame_height))

    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * frame_width, 0))

    return sheet


def unpack_sheet(
    sheet: Image.Image,
    frame_width: int,
) -> list[Image.Image]:
    """Unpack a horizontal strip into individual frame images.

    Args:
        sheet: Horizontal strip image.
        frame_width: Width of each frame.

    Returns:
        List of cropped frame images.
    """
    sheet_width, sheet_height = sheet.size
    frame_count = sheet_width // frame_width
    frames: list[Image.Image] = []

    for i in range(frame_count):
        box = (i * frame_width, 0, (i + 1) * frame_width, sheet_height)
        frames.append(sheet.crop(box))

    return frames


def palette_swap(
    img: Image.Image,
    source_palette: list[tuple[int, int, int]],
    target_palette: list[tuple[int, int, int]],
) -> Image.Image:
    """Recolor a sprite by mapping source palette colors to target palette.

    Each pixel is matched to the nearest source palette color, then
    replaced with the corresponding target palette color. Transparent
    pixels are left unchanged.

    Args:
        img: Source RGBA image.
        source_palette: Original colors to match against.
        target_palette: Replacement colors (same length as source).

    Returns:
        Recolored image.

    Raises:
        ValueError: If palettes have different lengths.
    """
    if len(source_palette) != len(target_palette):
        raise ValueError(
            f"Source and target palettes must be same length "
            f"({len(source_palette)} != {len(target_palette)})."
        )

    result = img.copy()
    pixels = result.load()
    width, height = result.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            # Find nearest source color
            best_idx = 0
            best_dist = _color_distance_sq((r, g, b), source_palette[0])
            for i in range(1, len(source_palette)):
                dist = _color_distance_sq((r, g, b), source_palette[i])
                if dist < best_dist:
                    best_idx = i
                    best_dist = dist
            # Replace with target
            t = target_palette[best_idx]
            pixels[x, y] = (t[0], t[1], t[2], a)

    return result


def _premultiply_alpha(img: Image.Image) -> Image.Image:
    """Premultiply RGB channels by alpha.

    Scales each color channel by the alpha value so that interpolation
    filters (LANCZOS, BOX) blend colors correctly near transparent edges.
    Without premultiplication, transparent pixels with undefined RGB (often
    black) bleed dark halos into neighboring opaque pixels during resize.

    Args:
        img: Source RGBA image.

    Returns:
        New image with premultiplied alpha.
    """
    r, g, b, a = img.split()
    # ImageChops.multiply: output = (channel * alpha) / 255
    r = ImageChops.multiply(r, a)
    g = ImageChops.multiply(g, a)
    b = ImageChops.multiply(b, a)
    return Image.merge("RGBA", (r, g, b, a))


def _unpremultiply_alpha(img: Image.Image) -> Image.Image:
    """Reverse premultiplied alpha: recover straight RGB from premultiplied.

    For each pixel: if alpha > 0, divide RGB by alpha/255.
    Transparent pixels are set to (0, 0, 0, 0).

    Args:
        img: Premultiplied RGBA image.

    Returns:
        New image with straight (non-premultiplied) alpha.
    """
    result = img.copy()
    pixels = result.load()
    width, height = result.size

    for y in range(height):
        for x in range(width):
            pr, pg, pb, pa = pixels[x, y]
            if pa == 0:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (
                    min(255, pr * 255 // pa),
                    min(255, pg * 255 // pa),
                    min(255, pb * 255 // pa),
                    pa,
                )

    return result


def resize_for_pixel_art(
    img: Image.Image,
    size: tuple[int, int],
    intermediate_scale: int = 2,
) -> Image.Image:
    """Downscale with area averaging for clean pixel art.

    Two-stage resize: LANCZOS to an intermediate size (for smooth color
    averaging), then nearest-neighbor to the final size (for crisp pixel
    edges). Uses premultiplied alpha during interpolation to prevent dark
    halo artifacts at transparent boundaries.

    For intermediate_scale=1, performs a single LANCZOS resize.
    When the source is already smaller than the intermediate target,
    falls back to direct LANCZOS (no benefit from an upscale stage).

    Args:
        img: Source RGBA image.
        size: Target (width, height).
        intermediate_scale: Multiplier for intermediate size (default 2).
            Higher values preserve more detail from the averaging step
            at the cost of a slightly softer final result.

    Returns:
        Resized image with clean pixel art edges.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Premultiply alpha to prevent dark fringing during interpolation
    premul = _premultiply_alpha(img)

    if intermediate_scale <= 1:
        resized = premul.resize(size, Image.LANCZOS)
    else:
        intermediate_size = (
            size[0] * intermediate_scale,
            size[1] * intermediate_scale,
        )
        # Only two-stage if source is larger than the intermediate target
        if (
            premul.size[0] <= intermediate_size[0]
            and premul.size[1] <= intermediate_size[1]
        ):
            resized = premul.resize(size, Image.LANCZOS)
        else:
            # Stage 1: LANCZOS — smooth area averaging
            intermediate = premul.resize(intermediate_size, Image.LANCZOS)
            # Stage 2: NEAREST — crisp pixel grid snap
            resized = intermediate.resize(size, Image.NEAREST)

    # Unpremultiply to recover straight alpha for downstream pipeline
    return _unpremultiply_alpha(resized)


def process_sprite(
    img: Image.Image,
    size: tuple[int, int],
    palette: list[tuple[int, int, int]],
    outline_color: tuple[int, int, int] = (20, 15, 25),
    intermediate_scale: int = 2,
    bg_tolerance: int = 40,
    alpha_threshold: int = 128,
) -> Image.Image:
    """Full sprite processing pipeline: background removal, resize, quantize, outline.

    Pipeline order (optimized for quality):
    1. Remove background (green-screen keying + edge flood fill)
    2. Clean alpha (binary mask at source resolution — sharp edges for resize)
    3. Two-stage downscale (LANCZOS averaging → nearest-neighbor crispness)
    4. Clean alpha (fix semi-transparent edges introduced by LANCZOS)
    5. Quantize to palette (snap averaged colors to defined palette)
    6. Enforce outline (1px dark border for readability at small sizes)

    Args:
        img: Source RGBA image (typically AI-generated concept art).
        size: Target sprite dimensions (width, height).
        palette: List of (R, G, B) colors for quantization.
        outline_color: (R, G, B) for the 1px outline. Defaults to near-black.
        intermediate_scale: Multiplier for two-stage resize (default 2).
        bg_tolerance: Color distance tolerance for background removal.
        alpha_threshold: Alpha cutoff for binary mask.

    Returns:
        Processed sprite ready for in-game use.

    Raises:
        ValueError: If palette is empty.
    """
    if not palette:
        raise ValueError("Palette must not be empty.")

    # Ensure RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 1. Remove background
    result = remove_background(img, tolerance=bg_tolerance)

    # 2. Clean alpha at source resolution (sharp mask before downscale)
    result = clean_alpha(result, threshold=alpha_threshold)

    # 3. Two-stage downscale with premultiplied alpha
    result = resize_for_pixel_art(result, size, intermediate_scale=intermediate_scale)

    # 4. Clean alpha again (LANCZOS creates semi-transparent edge pixels)
    result = clean_alpha(result, threshold=alpha_threshold)

    # 5. Quantize to palette
    result = quantize_to_palette(result, palette)

    # 6. Enforce outline
    result = enforce_outline(result, outline_color)

    return result
