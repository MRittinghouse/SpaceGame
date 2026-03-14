"""Generate 80x60 pixel art system portraits for the galaxy map.

Each system gets a unique scene built from procedural elements:
planets, stars, stations, asteroids, nebulae. Colors match the
faction palette defined in the visual spec.

Usage:
    python -m tools.generate_system_portraits
"""

import math
import random
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Requires Pillow: pip install Pillow")
    raise SystemExit(1)

OUTPUT_DIR = (
    Path(__file__).parent.parent
    / "spacegame"
    / "data"
    / "assets"
    / "sprites"
    / "systems"
)

W, H = 80, 60


# ==========================================================================
# Palette definitions per system (from visual spec mood palettes)
# ==========================================================================

SYSTEM_PALETTES = {
    "nexus_prime": {
        "bg": (12, 14, 30),
        "star": (255, 210, 80),
        "planet": (60, 70, 140),
        "accent": (200, 170, 60),
        "nebula": (40, 35, 80),
    },
    "stellaris_port": {
        "bg": (15, 12, 25),
        "star": (255, 220, 100),
        "planet": (180, 160, 100),
        "accent": (220, 190, 80),
        "nebula": (50, 40, 60),
    },
    "forgeworks": {
        "bg": (20, 10, 8),
        "star": (255, 140, 40),
        "planet": (140, 70, 30),
        "accent": (255, 100, 20),
        "nebula": (60, 25, 10),
    },
    "iron_depths": {
        "bg": (12, 12, 15),
        "star": (180, 170, 160),
        "planet": (80, 75, 70),
        "accent": (140, 120, 90),
        "nebula": (30, 28, 35),
    },
    "breakstone": {
        "bg": (18, 14, 10),
        "star": (220, 180, 100),
        "planet": (130, 100, 60),
        "accent": (180, 140, 60),
        "nebula": (45, 35, 20),
    },
    "axiom_labs": {
        "bg": (8, 15, 20),
        "star": (200, 240, 255),
        "planet": (60, 130, 150),
        "accent": (80, 200, 200),
        "nebula": (20, 40, 55),
    },
    "nova_research": {
        "bg": (10, 14, 20),
        "star": (160, 200, 240),
        "planet": (70, 100, 140),
        "accent": (80, 180, 140),
        "nebula": (25, 35, 50),
    },
    "havens_rest": {
        "bg": (8, 18, 12),
        "star": (220, 230, 180),
        "planet": (60, 130, 70),
        "accent": (140, 180, 100),
        "nebula": (20, 40, 25),
    },
    "verdant": {
        "bg": (8, 16, 10),
        "star": (240, 240, 180),
        "planet": (50, 140, 60),
        "accent": (100, 200, 120),
        "nebula": (15, 35, 20),
    },
    "crimson_reach": {
        "bg": (20, 8, 8),
        "star": (255, 80, 60),
        "planet": (120, 30, 30),
        "accent": (255, 60, 40),
        "nebula": (50, 15, 15),
    },
    "the_fulcrum": {
        "bg": (14, 12, 20),
        "star": (200, 180, 220),
        "planet": (80, 70, 110),
        "accent": (160, 140, 200),
        "nebula": (35, 30, 50),
    },
}


# ==========================================================================
# Drawing primitives
# ==========================================================================


def _draw_stars(draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict) -> None:
    """Scatter small background stars."""
    star_color = palette["star"]
    for _ in range(25):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        brightness = rng.randint(60, 200)
        r = min(255, star_color[0] * brightness // 255)
        g = min(255, star_color[1] * brightness // 255)
        b = min(255, star_color[2] * brightness // 255)
        alpha = rng.randint(100, 220)
        draw.point((x, y), fill=(r, g, b, alpha))


def _draw_nebula(
    img: Image.Image, rng: random.Random, palette: dict, cx: int, cy: int, size: int
) -> None:
    """Draw a soft nebula cloud as scattered transparent dots."""
    px = img.load()
    nc = palette["nebula"]
    for _ in range(size * 20):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.gauss(0, size * 0.4)
        x = int(cx + dist * math.cos(angle))
        y = int(cy + dist * 0.7 * math.sin(angle))
        if 0 <= x < W and 0 <= y < H:
            alpha = max(0, int(80 - abs(dist) * 2))
            if alpha > 0:
                r0, g0, b0, a0 = px[x, y]
                blend = alpha / 255.0
                nr = min(255, int(r0 * (1 - blend) + nc[0] * blend))
                ng = min(255, int(g0 * (1 - blend) + nc[1] * blend))
                nb = min(255, int(b0 * (1 - blend) + nc[2] * blend))
                px[x, y] = (nr, ng, nb, 255)


def _draw_planet(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    color: tuple,
    highlight: tuple,
) -> None:
    """Draw a planet with highlight crescent."""
    # Main body
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=color,
        outline=(max(0, color[0] - 30), max(0, color[1] - 30), max(0, color[2] - 30), 255),
    )
    # Highlight crescent (upper-left)
    hr = radius - 2
    if hr > 1:
        draw.arc(
            [cx - hr - 1, cy - hr - 1, cx + hr - 1, cy + hr - 1],
            200, 340,
            fill=(*highlight, 180),
            width=1,
        )


def _draw_ring(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, color: tuple) -> None:
    """Draw a planetary ring (elliptical)."""
    ring_w = radius + 5
    ring_h = radius // 3
    draw.ellipse(
        [cx - ring_w, cy - ring_h, cx + ring_w, cy + ring_h],
        outline=(*color[:3], 140),
    )


def _draw_station(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple) -> None:
    """Draw a small station icon (diamond shape)."""
    s = 3
    draw.polygon(
        [(x, y - s), (x + s, y), (x, y + s), (x - s, y)],
        fill=(*color[:3], 200),
        outline=(*color[:3], 255),
    )


def _draw_asteroids(draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict) -> None:
    """Draw scattered small asteroid dots."""
    for _ in range(8):
        x = rng.randint(5, W - 5)
        y = rng.randint(5, H - 5)
        r = rng.randint(1, 2)
        c = palette["planet"]
        brightness = rng.uniform(0.5, 1.0)
        ac = (int(c[0] * brightness), int(c[1] * brightness), int(c[2] * brightness), 200)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=ac)


def _draw_main_star(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    cx: int,
    cy: int,
    radius: int,
    color: tuple,
) -> None:
    """Draw the system's central star with glow."""
    # Glow
    px = img.load()
    for dy in range(-radius * 3, radius * 3 + 1):
        for dx in range(-radius * 3, radius * 3 + 1):
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < radius * 3:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < H:
                    falloff = max(0, 1.0 - dist / (radius * 3))
                    alpha = int(40 * falloff * falloff)
                    if alpha > 0:
                        r0, g0, b0, a0 = px[x, y]
                        blend = alpha / 255.0
                        nr = min(255, int(r0 + color[0] * blend))
                        ng = min(255, int(g0 + color[1] * blend))
                        nb = min(255, int(b0 + color[2] * blend))
                        px[x, y] = (nr, ng, nb, 255)
    # Core
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(*color[:3], 255),
    )


# ==========================================================================
# System-specific scene composers
# ==========================================================================


def _compose_trade_hub(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Trade hub: large station, medium planet, busy with small stations."""
    _draw_nebula(img, rng, palette, 60, 20, 15)
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 10, 10, 4, palette["star"])
    _draw_planet(draw, 55, 35, 12, (*palette["planet"], 255), palette["accent"])
    _draw_station(draw, 35, 25, palette["accent"])
    _draw_station(draw, 42, 40, palette["accent"])
    _draw_station(draw, 30, 45, palette["star"])


def _compose_agricultural(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Agricultural: large green planet dominates, gentle star."""
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 70, 8, 3, palette["star"])
    _draw_planet(draw, 35, 32, 18, (*palette["planet"], 255), palette["accent"])
    # Atmosphere glow
    draw.arc(
        [35 - 20, 32 - 20, 35 + 20, 32 + 20], 180, 360,
        fill=(*palette["accent"][:3], 60), width=2,
    )
    _draw_station(draw, 60, 42, palette["accent"])


def _compose_industrial(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Industrial: orange star, smoky planet, orbiting stations."""
    _draw_nebula(img, rng, palette, 40, 30, 20)
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 15, 15, 5, palette["star"])
    _draw_planet(draw, 50, 35, 13, (*palette["planet"], 255), palette["accent"])
    _draw_ring(draw, 50, 35, 13, palette["accent"])
    _draw_station(draw, 35, 48, palette["accent"])


def _compose_mining(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Mining: asteroid field, small rocky planet, dim star."""
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 65, 12, 3, palette["star"])
    _draw_planet(draw, 25, 35, 10, (*palette["planet"], 255), palette["accent"])
    _draw_asteroids(draw, rng, palette)
    _draw_asteroids(draw, rng, palette)
    _draw_station(draw, 40, 28, palette["accent"])


def _compose_research(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Research: glowing anomaly/nebula, small planet, clean station."""
    _draw_nebula(img, rng, palette, 40, 30, 25)
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 55, 10, 3, palette["star"])
    _draw_planet(draw, 30, 38, 9, (*palette["planet"], 255), palette["accent"])
    _draw_station(draw, 50, 35, palette["accent"])
    # Anomaly glow
    _draw_nebula(img, rng, palette, 20, 20, 10)


def _compose_frontier(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Frontier: red nebula, scattered debris, menacing."""
    _draw_nebula(img, rng, palette, 30, 25, 30)
    _draw_nebula(img, rng, palette, 55, 40, 18)
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 60, 15, 4, palette["star"])
    _draw_planet(draw, 30, 38, 11, (*palette["planet"], 255), palette["accent"])
    _draw_asteroids(draw, rng, palette)


def _compose_military(
    img: Image.Image, draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict
) -> None:
    """Military: fortified station, patrol ships, imposing."""
    _draw_nebula(img, rng, palette, 50, 25, 15)
    _draw_stars(draw, rng, palette)
    _draw_main_star(draw, img, 12, 12, 4, palette["star"])
    _draw_planet(draw, 50, 35, 14, (*palette["planet"], 255), palette["accent"])
    # Multiple stations (military fleet)
    _draw_station(draw, 30, 20, palette["accent"])
    _draw_station(draw, 38, 30, palette["accent"])
    _draw_station(draw, 25, 38, palette["star"])
    _draw_station(draw, 65, 48, palette["accent"])


COMPOSERS = {
    "trade_hub": _compose_trade_hub,
    "agricultural": _compose_agricultural,
    "industrial": _compose_industrial,
    "mining": _compose_mining,
    "research": _compose_research,
    "frontier": _compose_frontier,
    "military": _compose_military,
}


# ==========================================================================
# Main generation
# ==========================================================================


def generate_system_portrait(system_id: str, system_type: str) -> Image.Image:
    """Generate a single system portrait.

    Args:
        system_id: System identifier for palette lookup and RNG seed.
        system_type: System type for scene composition.

    Returns:
        80x60 RGBA Image.
    """
    palette = SYSTEM_PALETTES.get(system_id, SYSTEM_PALETTES["nexus_prime"])
    rng = random.Random(hash(system_id))

    img = Image.new("RGBA", (W, H), (*palette["bg"], 255))
    draw = ImageDraw.Draw(img)

    composer = COMPOSERS.get(system_type, _compose_trade_hub)
    composer(img, draw, rng, palette)

    return img


def generate_all() -> list[Path]:
    """Generate all system portraits from systems.json.

    Returns:
        List of generated file paths.
    """
    import json

    systems_path = Path(__file__).parent.parent / "data" / "galaxy" / "systems.json"
    data = json.load(open(systems_path))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = []

    for system in data["systems"]:
        sid = system["id"]
        stype = system["type"]
        img = generate_system_portrait(sid, stype)
        out_path = OUTPUT_DIR / f"{sid}.png"
        img.save(str(out_path), "PNG")
        paths.append(out_path)
        print(f"  {sid:20s} ({stype}) -> {out_path.name}")

    return paths


def main() -> None:
    print("Generating system portraits...")
    paths = generate_all()
    print(f"\nGenerated {len(paths)} system portraits in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
