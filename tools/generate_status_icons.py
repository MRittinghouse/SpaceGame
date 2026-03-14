"""Generate 12x12 pixel status effect icons for combat UI.

Creates a horizontal strip sprite sheet (96x12) with 8 icons,
one per EffectType. Saved to sprites/ui/status_icons.png.

Usage:
    python -m tools.generate_status_icons
"""

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
    / "ui"
)

ICON_SIZE = 12

# Icon order matches EFFECT_ICON_ORDER in combat_view.py
EFFECT_ORDER = [
    "damage",
    "shield_restore",
    "hull_restore",
    "evasion_mod",
    "accuracy_mod",
    "shield_drain",
    "damage_reduction",
    "energy_drain",
]


def _draw_damage(draw: ImageDraw.ImageDraw) -> None:
    """Red crosshair — damage dealt."""
    c = (220, 60, 40, 255)
    # Crosshair lines
    draw.line([(6, 1), (6, 11)], fill=c, width=1)
    draw.line([(1, 6), (11, 6)], fill=c, width=1)
    # Circle
    draw.ellipse([2, 2, 10, 10], outline=c)


def _draw_shield_restore(draw: ImageDraw.ImageDraw) -> None:
    """Blue shield with + sign."""
    sc = (80, 160, 255, 255)
    # Shield shape (chevron)
    draw.polygon([(6, 1), (10, 3), (10, 7), (6, 11), (2, 7), (2, 3)], outline=sc)
    # Plus
    bright = (160, 220, 255, 255)
    draw.line([(6, 4), (6, 8)], fill=bright, width=1)
    draw.line([(4, 6), (8, 6)], fill=bright, width=1)


def _draw_hull_restore(draw: ImageDraw.ImageDraw) -> None:
    """Green cross — hull repair."""
    gc = (60, 200, 80, 255)
    bright = (120, 255, 140, 255)
    # Cross shape
    draw.rectangle([5, 2, 7, 10], fill=gc)
    draw.rectangle([3, 4, 9, 8], fill=gc)
    # Bright center
    draw.point((6, 6), fill=bright)


def _draw_evasion_mod(draw: ImageDraw.ImageDraw) -> None:
    """Cyan speed arrows — evasion modifier."""
    ec = (80, 220, 220, 255)
    # Two chevron arrows pointing up-right
    draw.line([(2, 8), (6, 4), (10, 8)], fill=ec, width=1)
    draw.line([(2, 5), (6, 1), (10, 5)], fill=ec, width=1)


def _draw_accuracy_mod(draw: ImageDraw.ImageDraw) -> None:
    """Orange target reticle — accuracy modifier."""
    tc = (255, 160, 40, 255)
    # Outer ring
    draw.ellipse([1, 1, 11, 11], outline=tc)
    # Inner ring
    draw.ellipse([4, 4, 8, 8], outline=tc)
    # Center dot
    draw.point((6, 6), fill=(255, 200, 80, 255))


def _draw_shield_drain(draw: ImageDraw.ImageDraw) -> None:
    """Blue shield with crack/down arrow."""
    sc = (80, 120, 200, 255)
    # Shield outline
    draw.polygon([(6, 1), (10, 3), (10, 7), (6, 11), (2, 7), (2, 3)], outline=sc)
    # Crack/lightning bolt through it
    crack = (200, 80, 80, 255)
    draw.line([(5, 3), (7, 5), (5, 7), (7, 9)], fill=crack, width=1)


def _draw_damage_reduction(draw: ImageDraw.ImageDraw) -> None:
    """Gray-blue shield with absorb glow."""
    sc = (140, 160, 200, 255)
    # Thick shield
    draw.polygon([(6, 1), (10, 3), (10, 7), (6, 11), (2, 7), (2, 3)], fill=sc)
    # Inner highlight
    inner = (180, 200, 240, 255)
    draw.polygon([(6, 3), (8, 4), (8, 6), (6, 9), (4, 6), (4, 4)], fill=inner)


def _draw_energy_drain(draw: ImageDraw.ImageDraw) -> None:
    """Yellow lightning bolt — energy drain."""
    yc = (255, 200, 40, 255)
    bright = (255, 240, 120, 255)
    # Lightning bolt shape
    draw.polygon(
        [(7, 0), (3, 6), (6, 6), (5, 12), (9, 5), (6, 5)],
        fill=yc,
        outline=bright,
    )


ICON_DRAWERS = {
    "damage": _draw_damage,
    "shield_restore": _draw_shield_restore,
    "hull_restore": _draw_hull_restore,
    "evasion_mod": _draw_evasion_mod,
    "accuracy_mod": _draw_accuracy_mod,
    "shield_drain": _draw_shield_drain,
    "damage_reduction": _draw_damage_reduction,
    "energy_drain": _draw_energy_drain,
}


def generate_status_icons() -> Path:
    """Generate status_icons.png sprite sheet.

    Returns:
        Path to the generated file.
    """
    total_w = ICON_SIZE * len(EFFECT_ORDER)
    sheet = Image.new("RGBA", (total_w, ICON_SIZE), (0, 0, 0, 0))

    for i, effect_id in enumerate(EFFECT_ORDER):
        icon = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        ICON_DRAWERS[effect_id](draw)
        sheet.paste(icon, (i * ICON_SIZE, 0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "status_icons.png"
    sheet.save(out_path)
    return out_path


def main() -> None:
    path = generate_status_icons()
    print(f"Generated status icons: {path}")
    print(f"  {len(EFFECT_ORDER)} icons, {ICON_SIZE}x{ICON_SIZE}px each")
    print(f"  Sheet size: {ICON_SIZE * len(EFFECT_ORDER)}x{ICON_SIZE}")
    print(f"  Order: {', '.join(EFFECT_ORDER)}")


if __name__ == "__main__":
    main()
