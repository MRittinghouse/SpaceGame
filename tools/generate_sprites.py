"""Batch generate game sprites through DALL-E 3 + pixel art pipeline.

Generates sprites for all asset categories: faction emblems, player ships,
enemy ships, NPC portraits, upgrade icons, and ground tiles. Each category
has tailored prompts derived from the cultural guide and game data.

Usage:
    python tools/generate_sprites.py emblems              # Generate faction emblems
    python tools/generate_sprites.py ships_player          # Generate player ships
    python tools/generate_sprites.py ships_enemy           # Generate enemy base sprites
    python tools/generate_sprites.py portraits             # Generate NPC portraits
    python tools/generate_sprites.py upgrades              # Generate upgrade icons
    python tools/generate_sprites.py ground_tiles          # Generate ground tiles
    python tools/generate_sprites.py emblems --only commerce_guild  # Single asset
    python tools/generate_sprites.py ships_player --list   # List asset IDs
    python tools/generate_sprites.py --skip-existing       # Skip already generated
"""

import argparse
import json
import sys
import time
import pathlib
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.pixel_pipeline import process_sprite, resize_nearest

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

ASSETS_BASE = PROJECT_ROOT / "spacegame" / "data" / "assets"
OUTLINE_COLOR = (10, 10, 15)

# Style fragments reused across prompts
_GREEN_BG = "on a pure bright green background (#00FF00). "
_FLAT_VIEW = "Flat top-down 2D view, NOT isometric, NOT 3D. "
_BUST_VIEW = "Head-and-shoulders bust portrait, 3/4 view facing right. "
_ICON_STYLE = (
    "Style: 16-bit SNES-era pixel art, limited color palette, "
    "clean 1px dark outlines around the object. "
    "Single small centered object, large bright green margin around it. "
    "No text, no label, no frame, no border, no shadow, no ground plane, "
    "no other objects, no UI elements."
)
_SHIP_STYLE_PLAYER = (
    "Style: 16-bit SNES-era pixel art, limited color palette, "
    "clean 1px dark outlines. Top-down spaceship sprite, nose pointing RIGHT "
    "(engines/exhaust on the LEFT side). "
    "Single centered ship, large bright green margin around it. "
    "No text, no label, no frame, no shadow, no ground, no stars, "
    "no other objects, no UI elements."
)
_SHIP_STYLE_ENEMY = (
    "Style: 16-bit SNES-era pixel art, limited color palette, "
    "clean 1px dark outlines. Top-down spaceship sprite, nose pointing LEFT "
    "(engines/exhaust on the RIGHT side). "
    "Single centered ship, large bright green margin around it. "
    "No text, no label, no frame, no shadow, no ground, no stars, "
    "no other objects, no UI elements."
)
# Backward compat alias
_SHIP_STYLE = _SHIP_STYLE_PLAYER
_PORTRAIT_STYLE = (
    "Style: 16-bit SNES-era pixel art portrait, limited color palette, "
    "clean outlines. Head and shoulders bust, 3/4 view facing right. "
    "Dark space station interior background (NOT green screen). "
    "No text, no label, no frame, no UI. Expressive face, visible details."
)
_EMBLEM_STYLE = (
    "Style: 16-bit pixel art emblem/logo, limited color palette, "
    "clean geometric shapes with 1px dark outlines. "
    "Single centered symbol, large bright green margin around it. "
    "No text, no label, no frame, no shadow, no background details."
)


def load_palette(palette_name: str) -> list[tuple[int, int, int]]:
    """Load a palette from JSON."""
    path = ASSETS_BASE / "palettes" / f"{palette_name}.json"
    with open(path) as f:
        data = json.load(f)
    return [tuple(v) for v in data["colors"].values()]


# ---------------------------------------------------------------------------
# Category: Faction Emblems (24x24)
# ---------------------------------------------------------------------------

EMBLEM_SIZE = (24, 24)
EMBLEM_PROMPTS: dict[str, str] = {
    "commerce_guild": (
        "A faction emblem: a stylized golden balance scale " + _GREEN_BG +
        "Symmetrical design. Gold and dark navy colors. "
        "The scale represents fair trade and commerce. "
        "Corporate, authoritative, wealthy. Geometric and precise. " + _EMBLEM_STYLE
    ),
    "miners_union": (
        "A faction emblem: two crossed mining pickaxes over a gear " + _GREEN_BG +
        "Rust orange and dark gray colors. Industrial, strong, working-class. "
        "The pickaxes are sturdy and angular. Bold, blocky shapes. "
        "Represents solidarity and labor. " + _EMBLEM_STYLE
    ),
    "science_collective": (
        "A faction emblem: a stylized atom with orbiting electrons " + _GREEN_BG +
        "Teal, white, and steel blue colors. Clean, precise, scientific. "
        "Hexagonal lattice or atomic orbital motif. "
        "Clinical and elegant. Represents knowledge and progress. " + _EMBLEM_STYLE
    ),
    "frontier_alliance": (
        "A faction emblem: a compass rose star " + _GREEN_BG +
        "Forest green and tan colors with sky blue accent. "
        "Four-pointed star or compass design. "
        "Resourceful, independent, frontier spirit. "
        "Organic shapes, slightly rough-hewn. " + _EMBLEM_STYLE
    ),
    "crimson_reach": (
        "A faction emblem: a cracked skull with toxic green eyes " + _GREEN_BG +
        "Deep red, charcoal, and black colors with sickly green accent. "
        "Dangerous, lawless, menacing. Angular and threatening. "
        "Represents the lawless zone. " + _EMBLEM_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Player Ships (32x32)
# ---------------------------------------------------------------------------

SHIP_SIZE = (32, 32)
PLAYER_SHIP_PROMPTS: dict[str, str] = {
    "shuttle": (
        "A top-down pixel art spaceship: small civilian shuttle " + _GREEN_BG +
        "Compact, rounded hull. Single rear engine with orange glow. "
        "Blue-gray hull plating. Simple, reliable, utilitarian. "
        "The most common ship in the sector. Modest but functional. " + _SHIP_STYLE
    ),
    "light_freighter": (
        "A top-down pixel art spaceship: light cargo freighter " + _GREEN_BG +
        "Medium hull, visible cargo bay section in the middle. "
        "Two rear engines with orange glow. Blue-gray plating. "
        "The independent trader's workhorse. Balanced, dependable, no frills. " + _SHIP_STYLE
    ),
    "medium_freighter": (
        "A top-down pixel art spaceship: medium cargo freighter " + _GREEN_BG +
        "Larger boxy hull with visible cargo pod sections. "
        "Two rear engines. Steel-gray plating with industrial markings. "
        "Built for volume. Substantial cargo capacity. Functional. " + _SHIP_STYLE
    ),
    "fast_courier": (
        "A top-down pixel art spaceship: fast courier vessel " + _GREEN_BG +
        "Sleek, swept-back wings forming a narrow profile. "
        "Triple rear engines with bright orange glow. "
        "Dark blue hull, aerodynamic lines. Built for speed, not cargo. " + _SHIP_STYLE
    ),
    "armed_trader": (
        "A top-down pixel art spaceship: armed merchant vessel " + _GREEN_BG +
        "Freighter hull with visible weapon hardpoints on each side. "
        "Reinforced armor plating. Two engines. "
        "A freighter with teeth — practical combat modifications. "
        "Gray-blue hull with orange weapon accents. " + _SHIP_STYLE
    ),
    "scout_vessel": (
        "A top-down pixel art spaceship: long-range scout ship " + _GREEN_BG +
        "Elongated narrow hull with large sensor dish at the front. "
        "Oversized fuel tanks visible on sides. Two small engines. "
        "Sensor-heavy, exploration-focused. Teal-blue hull accents. " + _SHIP_STYLE
    ),
    "bulk_hauler": (
        "A top-down pixel art spaceship: massive bulk cargo hauler " + _GREEN_BG +
        "Very large, wide rectangular hull. Four rear engines. "
        "Visible antenna arrays and docking clamps. "
        "Industrial gray plating. Slow but enormous. "
        "The backbone of interstellar commerce. " + _SHIP_STYLE
    ),
    "clipper": (
        "A top-down pixel art spaceship: fast smuggling clipper " + _GREEN_BG +
        "Low-profile sleek hull, hard to detect. Dark coloring. "
        "Twin engines angled inward. Hidden compartment bulges barely visible. "
        "Dark charcoal hull with subtle purple accents. Stealthy. " + _SHIP_STYLE
    ),
    "luxury_yacht": (
        "A top-down pixel art spaceship: luxury executive yacht " + _GREEN_BG +
        "Elegant curved hull lines with glowing gold trim. "
        "Two engines with clean blue-white glow. "
        "Cream and gold hull plating. Polished, expensive. "
        "Diplomatic vessel. Exceptional quality. " + _SHIP_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Enemy Ships — Base Sprites (32x32)
# Faction variants are created via palette_swap after generation.
# ---------------------------------------------------------------------------

ENEMY_SHIP_PROMPTS: dict[str, str] = {
    "pirate_light": (
        "A top-down pixel art spaceship: small pirate raider " + _GREEN_BG +
        "Asymmetric hull cobbled from mismatched parts. "
        "Single oversized engine. Scavenged weapon mount on one side. "
        "Rust-brown and dark gray plating. Scrappy and fast. " + _SHIP_STYLE_ENEMY
    ),
    "pirate_medium": (
        "A top-down pixel art spaceship: pirate attack vessel " + _GREEN_BG +
        "Medium hull with mismatched armor plates welded on. "
        "Two engines of different sizes. Multiple weapon hardpoints. "
        "Dark gray with red-brown rust patches. Menacing silhouette. " + _SHIP_STYLE_ENEMY
    ),
    "pirate_heavy": (
        "A top-down pixel art spaceship: heavy pirate warship " + _GREEN_BG +
        "Large bulky hull made of welded-together ship carcasses. "
        "Three engines. Ram prow at the front. Bristling with weapons. "
        "Corroded dark metal with red accents. Intimidating. " + _SHIP_STYLE_ENEMY
    ),
    "patrol_craft": (
        "A top-down pixel art spaceship: military patrol vessel " + _GREEN_BG +
        "Symmetrical, clean-lined hull. Professional military design. "
        "Two rear engines. Shield emitters visible as blue dots. "
        "Silver-gray hull with blue accents. Regulation standard. " + _SHIP_STYLE_ENEMY
    ),
    "enforcer": (
        "A top-down pixel art spaceship: heavy enforcement cruiser " + _GREEN_BG +
        "Large well-armored symmetrical hull. Prominent shield arrays. "
        "Four engines. Multiple turret positions. "
        "Blue-silver plating. Corporate military. Methodical. " + _SHIP_STYLE_ENEMY
    ),
    "industrial_combat": (
        "A top-down pixel art spaceship: converted mining vessel " + _GREEN_BG +
        "Bulky industrial hull with exposed beams and machinery. "
        "Oversized engine nacelles. Repurposed drill as weapon. "
        "Rust-orange with yellow hazard stripes. Built tough. " + _SHIP_STYLE_ENEMY
    ),
    "science_vessel": (
        "A top-down pixel art spaceship: advanced research ship " + _GREEN_BG +
        "Smooth curved hull, distinctly different from angular ships. "
        "Prominent sensor dish. Integrated shield emitters. "
        "Teal and white coloring. Pulsing data lights. Elegant. " + _SHIP_STYLE_ENEMY
    ),
    "frontier_kitbash": (
        "A top-down pixel art spaceship: salvage-built fighter " + _GREEN_BG +
        "Asymmetric hull assembled from different ship parts. "
        "Mismatched hull plates in different colors. "
        "Visible repairs and jury-rigged components. "
        "Green and tan with bright accent patches. Folk art in space. " + _SHIP_STYLE_ENEMY
    ),
    "bounty_hunter": (
        "A top-down pixel art spaceship: bounty hunter interceptor " + _GREEN_BG +
        "Angular, predatory silhouette. Swept-forward weapon arms. "
        "Dark hull with red accent lighting. "
        "Purpose-built for hunting. Distinctive, aggressive profile. " + _SHIP_STYLE_ENEMY
    ),
    "reach_rustrunner": (
        "A top-down pixel art spaceship: scrapyard racer " + _GREEN_BG +
        "Corroded, skeletal hull frame with exposed reactor. "
        "Toxic green engine glow. Welded-on weapons. "
        "Dark red and charcoal with sickly green accents. "
        "Looks like it should fall apart but somehow flies. " + _SHIP_STYLE_ENEMY
    ),
    # --- Additional faction variety ---
    "guild_cruiser": (
        "A top-down pixel art spaceship: heavy corporate battlecruiser " + _GREEN_BG +
        "Massive symmetrical hull, broad and imposing. "
        "Six engines in a wide array. Layered armor plating, turret blisters. "
        "Navy blue with gold command bridge stripe. Capital ship. " + _SHIP_STYLE_ENEMY
    ),
    "union_barge": (
        "A top-down pixel art spaceship: heavy industrial barge " + _GREEN_BG +
        "Wide flat hull like a floating factory. Reinforced ram prow. "
        "Massive engine block at rear. Crane arms folded along sides. "
        "Rust-orange with yellow hazard markings. Built like a tank. " + _SHIP_STYLE_ENEMY
    ),
    "union_skiff": (
        "A top-down pixel art spaceship: small mining patrol boat " + _GREEN_BG +
        "Compact stubby hull, single large engine. "
        "Searchlight on nose. Workman's vessel. "
        "Rust-orange and dark gray. Simple, rugged, reliable. " + _SHIP_STYLE_ENEMY
    ),
    "science_frigate": (
        "A top-down pixel art spaceship: advanced science warship " + _GREEN_BG +
        "Sleek angular hull with integrated weapon arrays. "
        "Prominent energy capacitor banks along spine. Shield emitter rings. "
        "Teal and steel-white. Precise, technological, deadly. " + _SHIP_STYLE_ENEMY
    ),
    "science_drone": (
        "A top-down pixel art spaceship: small autonomous drone " + _GREEN_BG +
        "Tiny diamond-shaped hull, no cockpit visible. "
        "Single sensor eye at front. Micro-thrusters on all sides. "
        "White and teal. Robotic, efficient, swarm-like. " + _SHIP_STYLE_ENEMY
    ),
    "frontier_gunboat": (
        "A top-down pixel art spaceship: heavy frontier gunboat " + _GREEN_BG +
        "Boxy reinforced hull with oversized forward guns. "
        "Patchwork armor welded over a cargo frame. Two big engines. "
        "Green-brown with mismatched hull plates. A freighter turned warship. " + _SHIP_STYLE_ENEMY
    ),
    "frontier_scout": (
        "A top-down pixel art spaceship: light frontier scout " + _GREEN_BG +
        "Small nimble hull with oversized engine for its size. "
        "Antenna array on top. Light frame, fast and agile. "
        "Tan and green. Scrappy but quick. " + _SHIP_STYLE_ENEMY
    ),
    "reach_wrecker": (
        "A top-down pixel art spaceship: medium scrapyard destroyer " + _GREEN_BG +
        "Brutal angular hull made from salvaged warship plating. "
        "Saw-blade ram mounted at prow. Two mismatched engines. "
        "Dark red and black with rust. Built to rip ships apart. " + _SHIP_STYLE_ENEMY
    ),
    "reach_hulk": (
        "A top-down pixel art spaceship: massive scrapyard dreadnought " + _GREEN_BG +
        "Enormous hull assembled from multiple wrecked ships welded together. "
        "Four engines of different types. Bristling with scavenged weapons. "
        "Dark charcoal and deep red with toxic green reactor glow. "
        "A floating junkyard fortress. Terrifying. " + _SHIP_STYLE_ENEMY
    ),
    "bounty_cruiser": (
        "A top-down pixel art spaceship: heavy bounty hunter cruiser " + _GREEN_BG +
        "Wide aggressive hull with forward-swept weapon pods. "
        "Heavy armor and prominent engine array. Tracking dishes. "
        "Dark gunmetal with red accent striping. Relentless pursuit vessel. " + _SHIP_STYLE_ENEMY
    ),
    "smuggler_runner": (
        "A top-down pixel art spaceship: fast smuggler blockade runner " + _GREEN_BG +
        "Narrow dart-shaped hull, minimal profile. "
        "Oversized twin engines, tiny cargo section hidden inside. "
        "Matte dark gray with no markings. Designed to be invisible. " + _SHIP_STYLE_ENEMY
    ),
    "ledger_warship": (
        "A top-down pixel art spaceship: military-grade pirate warship " + _GREEN_BG +
        "Clearly a stolen military cruiser with pirate modifications. "
        "Clean lines marred by welded-on extra weapons and red paint. "
        "Navy blue base with crimson slashes. Professional pirates. " + _SHIP_STYLE_ENEMY
    ),
    # --- Missing enemies (14 ships added 2026-03-29) ---
    "armored_transport": (
        "A top-down pixel art spaceship: heavily armored cargo hauler " + _GREEN_BG +
        "Large bulky rectangular body with reinforced plate textures. "
        "Dark gray hull, small orange engine glow, cargo container shapes visible. "
        "Minimal weapons. Tough, slow, industrial. " + _SHIP_STYLE_ENEMY
    ),
    "cryo_interceptor": (
        "A top-down pixel art spaceship: fast cryo-weapon interceptor " + _GREEN_BG +
        "Narrow sleek angular wedge shape. White-blue hull. "
        "Ice-crystal blue weapon tips on wings, cyan engine trail. "
        "Fast and cold. Frost effect on hull edges. " + _SHIP_STYLE_ENEMY
    ),
    "ghost_raider": (
        "A top-down pixel art spaceship: stealth raider " + _GREEN_BG +
        "Low-profile angular shape, very dark gray near-black hull. "
        "Faint cyan edge lighting, minimal silhouette. "
        "Stealth panels, dim engine signature. Nearly invisible. " + _SHIP_STYLE_ENEMY
    ),
    "guild_arbiter": (
        "A top-down pixel art spaceship: trade authority enforcement vessel " + _GREEN_BG +
        "Medium-large authoritative wedge with command bridge. "
        "White hull with gold trim and official stripes. "
        "Sensor dish, weapon turrets. Professional and imposing. " + _SHIP_STYLE_ENEMY
    ),
    "ion_striker": (
        "A top-down pixel art spaceship: fast ion-weapon attack craft " + _GREEN_BG +
        "Small dart-like profile. Dark blue hull. "
        "Bright electric yellow-blue weapon glow on twin nose emitters. "
        "Fast, agile, crackling with energy. " + _SHIP_STYLE_ENEMY
    ),
    "plasma_bomber": (
        "A top-down pixel art spaceship: heavy plasma bomber " + _GREEN_BG +
        "Wide bulky bomber silhouette. Dark red-brown hull. "
        "Orange-red plasma glow from underslung bomb bays. "
        "Wide wing profile. Heavy and destructive. " + _SHIP_STYLE_ENEMY
    ),
    "rogue_ai_vessel": (
        "A top-down pixel art spaceship: autonomous AI ship " + _GREEN_BG +
        "Angular hexagonal geometric shape. White-light gray hull. "
        "Single red sensor eye, precise edges, no organic curves. "
        "Mechanical, alien, precise. " + _SHIP_STYLE_ENEMY
    ),
    "shield_drone": (
        "A top-down pixel art spaceship: small shield support drone " + _GREEN_BG +
        "Small compact spherical or octagonal shape. "
        "Blue-white body with bright blue shield bubble aura. "
        "Central core with radiating emitter lines. Tiny. " + _SHIP_STYLE_ENEMY
    ),
    "support_frigate": (
        "A top-down pixel art spaceship: medium support frigate " + _GREEN_BG +
        "Medium elongated hull. White with green accent stripe. "
        "Repair beam emitter with green glow, antenna array. "
        "Medical cross motif. Supportive, not aggressive. " + _SHIP_STYLE_ENEMY
    ),
    "corsair_king": (
        "A top-down pixel art spaceship: MASSIVE pirate flagship boss " + _GREEN_BG +
        "Fills the entire frame. Dark crimson hull with gold trim. "
        "Bristling weapon batteries everywhere, armored prow. "
        "Crown motif, terrifying warship. The most dangerous ship. " + _SHIP_STYLE_ENEMY
    ),
    "iron_maw": (
        "A top-down pixel art spaceship: MASSIVE industrial fortress-ship boss " + _GREEN_BG +
        "Fills the entire frame. Dark iron-rust hull. "
        "Open furnace maw at front with molten orange glow. "
        "Smokestacks, grinding teeth shapes. Industrial nightmare. " + _SHIP_STYLE_ENEMY
    ),
    "ledger_phantom": (
        "A top-down pixel art spaceship: ethereal ghost ship boss " + _GREEN_BG +
        "Medium-large hull that seems to fade at the edges. "
        "Very dark with ghostly blue-white glow and data-stream lines. "
        "Spectral, translucent feel. Haunted and dangerous. " + _SHIP_STYLE_ENEMY
    ),
    "the_collector": (
        "A top-down pixel art spaceship: bizarre trophy hunter boss ship " + _GREEN_BG +
        "Fills the frame. Asymmetric unusual silhouette. "
        "Dark hull covered in different-colored salvaged fragments. "
        "Green tractor beam glow, trophy spikes. Patchwork horror. " + _SHIP_STYLE_ENEMY
    ),
    "void_leviathan": (
        "A top-down pixel art spaceship: organic cosmic horror boss " + _GREEN_BG +
        "Fills the entire frame. Deep purple-black with organic curves. "
        "Bioluminescent magenta-violet glow lines, tentacle appendages. "
        "Glowing void eyes. Eldritch, alien, terrifying. " + _SHIP_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: NPC Portraits (50x60)
# ---------------------------------------------------------------------------

PORTRAIT_SIZE = (50, 60)
PORTRAIT_PROMPTS: dict[str, str] = {
    "officer_larsen": (
        "Pixel art portrait of a stern middle-aged male customs officer. " +
        _BUST_VIEW +
        "Clean-shaven, sharp jaw, military-short gray-streaked brown hair. "
        "Commerce Guild navy-blue uniform with gold rank insignia. "
        "Professional, authoritative expression. Slight frown. "
        "Blue-silver color scheme. " + _PORTRAIT_STYLE
    ),
    "odom_broker": (
        "Pixel art portrait of a busy middle-aged merchant. " +
        _BUST_VIEW +
        "Weathered face, short beard, trade-worn clothing. "
        "Utilitarian jumpsuit with cargo pockets. Neutral expression. "
        "Brown and gray tones. Working trader, not wealthy. " + _PORTRAIT_STYLE
    ),
    "elena_reeves": (
        "Pixel art portrait of a sharp-eyed female navigator in her 30s. " +
        _BUST_VIEW +
        "Dark hair pulled back, alert dark eyes, confident expression. "
        "Practical flight jacket with navigation patches. "
        "Warm skin tones. Competent and reliable. " + _PORTRAIT_STYLE
    ),
    "marcus_jin": (
        "Pixel art portrait of a broad-shouldered male mining foreman. " +
        _BUST_VIEW +
        "East Asian features, strong build, close-cropped black hair. "
        "Miners Union rust-orange work coveralls with tool harness. "
        "Serious but kind expression. Weathered hands. " + _PORTRAIT_STYLE
    ),
    "dr_priya_osei": (
        "Pixel art portrait of an elegant female research director. " +
        _BUST_VIEW +
        "South Asian features, dark skin, silver-streaked black hair in a neat bun. "
        "Science Collective white lab coat with teal accent trim. "
        "Intelligent, measured expression. Reading glasses. " + _PORTRAIT_STYLE
    ),
    "tomas_drifter": (
        "Pixel art portrait of a wiry young male frontier scout. " +
        _BUST_VIEW +
        "Tanned skin, sandy brown messy hair, quick eyes. "
        "Frontier Alliance green-brown scout gear, patched and worn. "
        "Easy grin, adventurous look. Resourceful. " + _PORTRAIT_STYLE
    ),
    "hanna_voss": (
        "Pixel art portrait of a tough female dock boss. " +
        _BUST_VIEW +
        "Muscular build, short platinum-blonde hair, burn scar on cheek. "
        "Miners Union foreman vest over tank top. Heavy gloves. "
        "No-nonsense expression. Respect earned through work. " + _PORTRAIT_STYLE
    ),
    "reva_sato": (
        "Pixel art portrait of a disciplined female military captain. " +
        _BUST_VIEW +
        "Japanese features, black hair in a tight braid, sharp eyes. "
        "Commerce Guild naval uniform, decorated. "
        "Composed, authoritative. A convoy escort commander. " + _PORTRAIT_STYLE
    ),
    "dex_halloran": (
        "Pixel art portrait of a shrewd male information broker. " +
        _BUST_VIEW +
        "Lean face, knowing smirk, dark eyes that miss nothing. "
        "Civilian clothes — dark jacket, high collar. "
        "Crimson Reach aesthetic — dark reds and charcoal. "
        "Untrustworthy but useful. " + _PORTRAIT_STYLE
    ),
    "malia_torres": (
        "Pixel art portrait of a weathered female salvage boss. " +
        _BUST_VIEW +
        "Latina features, dark curly hair tied back, grease-smudged face. "
        "Heavy salvage gear, welding goggles pushed up on forehead. "
        "Tough, practical, commanding. Warm earth tones. " + _PORTRAIT_STYLE
    ),
    "oren_tak": (
        "Pixel art portrait of an elderly male retired miner. " +
        _BUST_VIEW +
        "Deeply lined face, white beard, missing part of left ear. "
        "Worn Union coveralls, faded. Wise, tired eyes. "
        "Rust-orange and brown tones. Decades of hard work visible. " + _PORTRAIT_STYLE
    ),
    "sienna_vek": (
        "Pixel art portrait of a young female systems engineer. " +
        _BUST_VIEW +
        "Short asymmetric haircut, bright curious eyes, freckles. "
        "Science Collective tech uniform with data-pad holster. "
        "Teal and white colors. Enthusiastic, clever expression. " + _PORTRAIT_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Upgrade Icons (16x16)
# ---------------------------------------------------------------------------

UPGRADE_SIZE = (16, 16)
UPGRADE_PROMPTS: dict[str, str] = {
    # Weapons
    "salvaged_pulse_emitter": (
        "A small weapon icon: a crude pulse gun " + _GREEN_BG + _FLAT_VIEW +
        "Boxy salvaged energy weapon. Gray metal with orange power indicator. "
        "Scrappy, makeshift but functional. " + _ICON_STYLE
    ),
    "mining_laser_retrofit": (
        "A small weapon icon: a converted mining laser " + _GREEN_BG + _FLAT_VIEW +
        "Industrial cutting laser repurposed as weapon. "
        "Yellow-orange beam emitter. Rust-brown housing. " + _ICON_STYLE
    ),
    "laser_cannon": (
        "A small weapon icon: a laser cannon barrel " + _GREEN_BG + _FLAT_VIEW +
        "Clean military-grade laser weapon. Steel barrel with blue energy glow. "
        "Professional, well-built. " + _ICON_STYLE
    ),
    "dual_laser": (
        "A small weapon icon: twin laser barrels " + _GREEN_BG + _FLAT_VIEW +
        "Two parallel laser cannons mounted together. "
        "Blue-white energy glow at tips. Dark metal housing. " + _ICON_STYLE
    ),
    "missile_launcher": (
        "A small weapon icon: a missile launcher pod " + _GREEN_BG + _FLAT_VIEW +
        "Compact missile rack with visible warhead tips. "
        "Dark green-gray military coloring with red warhead tips. " + _ICON_STYLE
    ),
    "ion_disruptor": (
        "A small weapon icon: an ion disruption device " + _GREEN_BG + _FLAT_VIEW +
        "Sleek energy weapon with crackling blue-purple energy. "
        "Advanced technology look. Teal and white housing. " + _ICON_STYLE
    ),
    "plasma_torpedo": (
        "A small weapon icon: a plasma torpedo tube " + _GREEN_BG + _FLAT_VIEW +
        "Heavy weapon with glowing orange-red plasma chamber. "
        "Dangerous, high-powered. Dark metal with heat vents. " + _ICON_STYLE
    ),
    # Defense
    "basic_shield_gen": (
        "A small defense icon: a shield generator device " + _GREEN_BG + _FLAT_VIEW +
        "Compact dome-shaped device with cyan energy glow. "
        "Shield emitter technology. Blue and silver. " + _ICON_STYLE
    ),
    "armor_plating": (
        "A small defense icon: a reinforced armor plate " + _GREEN_BG + _FLAT_VIEW +
        "Thick layered metal plate with rivets. Heavy, protective. "
        "Dark steel gray. Industrial and solid. " + _ICON_STYLE
    ),
    "point_defense": (
        "A small defense icon: an automated turret " + _GREEN_BG + _FLAT_VIEW +
        "Small rapid-fire point defense turret. "
        "Gray with tracking sensor (red dot). Compact. " + _ICON_STYLE
    ),
    "emergency_repair": (
        "A small utility icon: a repair kit " + _GREEN_BG + _FLAT_VIEW +
        "Compact emergency repair module with wrench symbol. "
        "Green health cross indicator. Metal case. " + _ICON_STYLE
    ),
    "advanced_shield": (
        "A small defense icon: an advanced shield array " + _GREEN_BG + _FLAT_VIEW +
        "Sophisticated multi-emitter shield device. "
        "Bright cyan glow, multiple projector nodes. High-tech. " + _ICON_STYLE
    ),
    # Utility
    "cargo_bay_ext": (
        "A small utility icon: a cargo bay extension " + _GREEN_BG + _FLAT_VIEW +
        "Modular cargo container with expansion arrows. "
        "Brown-gray crate with reinforced corners. " + _ICON_STYLE
    ),
    "fuel_tank_upgrade": (
        "A small utility icon: a fuel tank " + _GREEN_BG + _FLAT_VIEW +
        "Cylindrical fuel tank with orange fuel indicator gauge. "
        "Dark metal with fuel warning stripes. " + _ICON_STYLE
    ),
    "efficient_engines": (
        "A small utility icon: an engine thruster " + _GREEN_BG + _FLAT_VIEW +
        "Sleek engine nozzle with bright orange thrust glow. "
        "Clean, efficient design. Silver-blue housing. " + _ICON_STYLE
    ),
    "emergency_thrusters": (
        "A small utility icon: emergency booster rockets " + _GREEN_BG + _FLAT_VIEW +
        "Twin small booster rockets with bright orange flame. "
        "Red emergency coloring. Compact, powerful. " + _ICON_STYLE
    ),
    "mining_drill_mk2": (
        "A small utility icon: an upgraded mining drill " + _GREEN_BG + _FLAT_VIEW +
        "Heavy drill bit with orange heat glow at tip. "
        "Industrial rust-brown housing. Upgraded with visible improvements. " + _ICON_STYLE
    ),
    "advanced_scanner": (
        "A small utility icon: a scanning dish " + _GREEN_BG + _FLAT_VIEW +
        "Small radar/sensor dish with teal scanning beam. "
        "High-tech, precise. White and teal coloring. " + _ICON_STYLE
    ),
    # Smuggling
    "hidden_compartment": (
        "A small utility icon: a secret hidden panel " + _GREEN_BG + _FLAT_VIEW +
        "Floor panel slightly ajar revealing hidden space beneath. "
        "Dark gray with subtle purple accent. Covert. " + _ICON_STYLE
    ),
    "signal_jammer": (
        "A small utility icon: an electronic jammer device " + _GREEN_BG + _FLAT_VIEW +
        "Compact electronics box with crackling red interference waves. "
        "Dark casing. Illicit-looking tech. " + _ICON_STYLE
    ),
    "false_transponder": (
        "A small utility icon: a forged ID transponder chip " + _GREEN_BG + _FLAT_VIEW +
        "Small chip with dual-color indicator (green/red). "
        "Deceptive device, looks innocent. Dark with amber LED. " + _ICON_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Mining Rocks (32x32)
# ---------------------------------------------------------------------------

MINING_ROCK_SIZE = (32, 32)

_ROCK_STYLE = (
    "Style: 16-bit pixel art asteroid/ore rock, limited color palette, "
    "clean dark outlines. Top-down view of a single floating space rock. "
    "The rock should be roughly circular/oval and fill about 70-80% of the frame. "
    "Single rock on green background, nothing else. "
    "No text, no label, no shadow, no ground, no stars, no other objects."
)

MINING_ROCK_PROMPTS: dict[str, str] = {
    # COMMON (raw ore) — 3 variants: gray-brown, dull, generic asteroid
    "rock_raw_ore_v1": (
        "A space rock: common asteroid chunk " + _GREEN_BG + _FLAT_VIEW +
        "Rough gray-brown surface with pockmarks and small craters. "
        "Dull, unrefined, generic. Mostly gray with brown patches. " + _ROCK_STYLE
    ),
    "rock_raw_ore_v2": (
        "A space rock: common asteroid fragment " + _GREEN_BG + _FLAT_VIEW +
        "Jagged gray rock with visible fracture lines. "
        "Slightly more angular shape than round. Dusty gray surface. " + _ROCK_STYLE
    ),
    "rock_raw_ore_v3": (
        "A space rock: small common asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Rounded gray-brown pebble with minor surface detail. "
        "Smooth-ish surface, unremarkable. Light gray with dark spots. " + _ROCK_STYLE
    ),
    # IRON — 3 variants: rusty red-brown with metallic veins
    "rock_iron_ore_v1": (
        "A space rock: iron-rich asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark brown rock with distinct rust-red veins running through it. "
        "Metallic reddish-orange streaks visible in the surface. Heavy look. " + _ROCK_STYLE
    ),
    "rock_iron_ore_v2": (
        "A space rock: iron ore deposit " + _GREEN_BG + _FLAT_VIEW +
        "Reddish-brown rock with patches of exposed dark metallic iron. "
        "Oxidized surface, warm rust tones. Chunky, solid appearance. " + _ROCK_STYLE
    ),
    "rock_iron_ore_v3": (
        "A space rock: iron-bearing asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Mostly dark rock with bright rust-orange bands across the surface. "
        "Iron deposits gleam slightly. Angular, fractured shape. " + _ROCK_STYLE
    ),
    # CRYSTAL — 3 variants: dark rock with bright cyan/blue crystal formations
    "rock_crystal_ore_v1": (
        "A space rock: crystal-encrusted asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark gray rock with bright cyan-blue crystal formations growing from it. "
        "Glowing blue crystal spikes on the surface. Magical, valuable look. " + _ROCK_STYLE
    ),
    "rock_crystal_ore_v2": (
        "A space rock: crystal-veined asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark rock with veins of bright teal-cyan crystal running through it. "
        "Crystal formations cluster on one side. Shimmering blue glow. " + _ROCK_STYLE
    ),
    "rock_crystal_ore_v3": (
        "A space rock: crystal cluster asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Small dark rock almost entirely covered in bright blue-cyan crystals. "
        "Dense crystal growth, very valuable appearance. Glittering surface. " + _ROCK_STYLE
    ),
    # RARE — 3 variants: dark rock with pink/magenta gem glints
    "rock_rare_ore_v1": (
        "A space rock: rare gem-bearing asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Very dark rock with scattered bright pink-magenta gem fragments visible. "
        "Rare and precious looking. Deep purple-black base with gem sparkles. " + _ROCK_STYLE
    ),
    "rock_rare_ore_v2": (
        "A space rock: rare mineral asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark violet-black rock with prominent magenta crystal inclusions. "
        "Rich, exotic appearance. Pink gems catch the light. " + _ROCK_STYLE
    ),
    "rock_rare_ore_v3": (
        "A space rock: rare precious ore " + _GREEN_BG + _FLAT_VIEW +
        "Near-black rock with a cluster of bright pink-purple gems embedded in it. "
        "Extremely valuable appearance. Rare metals glint within. " + _ROCK_STYLE
    ),
    # DENSE — 3 variants: heavy dark gray, metallic sheen, solid
    "rock_common_metals_v1": (
        "A space rock: dense metallic asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Very dark gray, almost black rock with a subtle metallic sheen. "
        "Extremely heavy and compact looking. Dense, no visible pores. " + _ROCK_STYLE
    ),
    "rock_common_metals_v2": (
        "A space rock: dense ore deposit " + _GREEN_BG + _FLAT_VIEW +
        "Heavy dark gray rock with bands of dark silver metal visible. "
        "Polished-looking surfaces where metal is exposed. Weighty. " + _ROCK_STYLE
    ),
    "rock_common_metals_v3": (
        "A space rock: dense metallic chunk " + _GREEN_BG + _FLAT_VIEW +
        "Dark gunmetal gray rock, almost entirely metallic. "
        "Smooth, heavy, industrially useful appearance. Steel-like sheen. " + _ROCK_STYLE
    ),
    # VOLATILE — 3 variants: cracked with orange/red glow from fissures
    "rock_unstable_v1": (
        "A space rock: volatile unstable asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark rock with visible cracks glowing bright orange-red from within. "
        "Dangerous, about to explode. Lava-like glow in fissures. Menacing. " + _ROCK_STYLE
    ),
    "rock_unstable_v2": (
        "A space rock: unstable explosive asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Cracked dark rock with red-hot interior visible through fracture lines. "
        "Pulsing with heat. Small flames or sparks at crack edges. " + _ROCK_STYLE
    ),
    "rock_unstable_v3": (
        "A space rock: volatile ore chunk " + _GREEN_BG + _FLAT_VIEW +
        "Nearly shattered rock held together by glowing orange energy. "
        "Major cracks emit bright orange light. Unstable, could blow any moment. " + _ROCK_STYLE
    ),
    # MONOLITH — 1 variant: alien, mysterious, dark with faint glow
    "rock_monolith_v1": (
        "A space rock: alien monolith artifact " + _GREEN_BG + _FLAT_VIEW +
        "Perfectly smooth rectangular dark slab unlike natural rock. "
        "Alien origin. Faint white-blue glow along edges. Mysterious, ancient. "
        "Geometric, unnatural shape among natural asteroids. " + _ROCK_STYLE
    ),
    # PRESSURE VENT — 2 variants: vent hole with steam/gas
    "rock_vent_v1": (
        "A space rock: pressure vent asteroid " + _GREEN_BG + _FLAT_VIEW +
        "Dark rock with a central vent hole emitting green-yellow gas. "
        "Hazardous fumes visible. Warning-colored gas wisps rising. " + _ROCK_STYLE
    ),
    "rock_vent_v2": (
        "A space rock: steaming vent rock " + _GREEN_BG + _FLAT_VIEW +
        "Porous dark rock with multiple small vents releasing toxic vapor. "
        "Green-tinted gas clouds. Dangerous, corroded surface. " + _ROCK_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Salvage Cells & Derelicts (32x32 cells, 160x120 backgrounds)
# ---------------------------------------------------------------------------

SALVAGE_CELL_SIZE = (32, 32)
SALVAGE_BG_SIZE = (160, 120)

_SALVAGE_CELL_STYLE = (
    "Style: 16-bit pixel art sci-fi panel/cell, limited color palette, "
    "clean dark outlines. Top-down view of a single spaceship hull panel. "
    "Square shape filling about 80% of the frame. "
    "Single object on green background, nothing else. "
    "No text, no label, no shadow, no stars, no other objects."
)

_SALVAGE_BG_STYLE = (
    "Style: 16-bit pixel art spaceship interior, limited color palette. "
    "Top-down view of a derelict spaceship room interior. "
    "Dark, damaged, atmospheric. Debris scattered. Emergency lighting. "
    "No text, no label, no UI elements."
)

SALVAGE_CELL_PROMPTS: dict[str, str] = {
    # Cell states — what each grid cell looks like
    "salvage_cell_hidden": (
        "A spaceship hull panel: sealed, unexplored " + _GREEN_BG + _FLAT_VIEW +
        "Dark metallic panel with rivets along edges. Unknown contents behind it. "
        "Steel-blue dark metal, slightly corroded. Mystery and danger. " + _SALVAGE_CELL_STYLE
    ),
    "salvage_cell_scanned": (
        "A spaceship hull panel: scanned, contents detected " + _GREEN_BG + _FLAT_VIEW +
        "Metallic panel with a faint cyan holographic scan overlay. "
        "Blue scan lines visible across the surface. Data readout feel. " + _SALVAGE_CELL_STYLE
    ),
    "salvage_cell_item": (
        "A spaceship hull panel: opened, item visible inside " + _GREEN_BG + _FLAT_VIEW +
        "Open panel revealing glowing salvageable components inside. "
        "Yellow-gold glow from valuable items. Wires and circuits visible. " + _SALVAGE_CELL_STYLE
    ),
    "salvage_cell_extracted": (
        "A spaceship hull panel: emptied after extraction " + _GREEN_BG + _FLAT_VIEW +
        "Open panel, empty interior, extracted clean. Hollow inside. "
        "Dark empty cavity, scorch marks, tool scratches. Used up. " + _SALVAGE_CELL_STYLE
    ),
    # Quality frames — visual border indicating item rarity
    "quality_frame_poor": (
        "A small square frame border: common/poor quality indicator " + _GREEN_BG + _FLAT_VIEW +
        "Thin gray border frame. Simple, unremarkable. Dull metal edge. "
        "Style: 16-bit pixel art, 20x20, clean lines, just the border frame. "
        "No fill, no center content, just an empty square frame. "
        "No text, no label, no shadow."
    ),
    "quality_frame_normal": (
        "A small square frame border: normal quality indicator " + _GREEN_BG + _FLAT_VIEW +
        "Green-tinted border frame. Decent quality. Clean metal edge. "
        "Style: 16-bit pixel art, 20x20, clean lines, just the border frame. "
        "No fill, no center content, just an empty square frame. "
        "No text, no label, no shadow."
    ),
    "quality_frame_good": (
        "A small square frame border: good quality indicator " + _GREEN_BG + _FLAT_VIEW +
        "Blue-tinted border frame. High quality item. Polished edge. "
        "Style: 16-bit pixel art, 20x20, clean lines, just the border frame. "
        "No fill, no center content, just an empty square frame. "
        "No text, no label, no shadow."
    ),
    "quality_frame_excellent": (
        "A small square frame border: excellent/rare quality indicator " + _GREEN_BG + _FLAT_VIEW +
        "Gold-glowing border frame. Exceptional quality. Ornate edge. "
        "Style: 16-bit pixel art, 20x20, clean lines, just the border frame. "
        "No fill, no center content, just an empty square frame. "
        "No text, no label, no shadow."
    ),
    # Mode icons — scan and extract tools
    "icon_scan_mode": (
        "A small utility icon: scanner/radar pulse " + _GREEN_BG + _FLAT_VIEW +
        "Cyan radar sweep icon, circular pulse emanating outward. "
        "Scanning tool, detection device. Blue-cyan color. " + _ICON_STYLE
    ),
    "icon_extract_mode": (
        "A small utility icon: extraction tool/claw " + _GREEN_BG + _FLAT_VIEW +
        "Orange mechanical extraction claw or grapple icon. "
        "Salvage tool, grabbing device. Orange-gold color. " + _ICON_STYLE
    ),
}

SALVAGE_BG_PROMPTS: dict[str, str] = {
    "derelict_cargo_bay": (
        "Top-down pixel art interior: derelict spaceship cargo bay " +
        "Damaged cargo containers scattered across a metal floor. "
        "Emergency red lighting. Breach damage visible. Floating debris. "
        "Dark atmosphere, abandoned and dangerous. Wide open space. " + _SALVAGE_BG_STYLE
    ),
    "derelict_engine_room": (
        "Top-down pixel art interior: derelict spaceship engine room " +
        "Massive broken engine core in center, coolant pipes burst. "
        "Sparking electrical conduits. Green coolant puddles on floor. "
        "Dark, industrial, mechanical. Tight corridors between machinery. " + _SALVAGE_BG_STYLE
    ),
    "derelict_lab_module": (
        "Top-down pixel art interior: derelict spaceship science lab " +
        "Shattered glass containers, overturned research equipment. "
        "Blue holographic displays still flickering. Data terminals cracked. "
        "Clinical white surfaces now stained and damaged. Eerie glow. " + _SALVAGE_BG_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Ground Tiles (16x16)
# ---------------------------------------------------------------------------

GROUND_TILE_SIZE = (16, 16)
GROUND_TILE_PROMPTS: dict[str, str] = {
    "floor": (
        "A top-down tile: metal floor panel " + _GREEN_BG + _FLAT_VIEW +
        "Industrial sci-fi metal floor grating. Subtle grid pattern. "
        "Dark gray-blue metal. Clean, walkable surface. " + _ICON_STYLE
    ),
    "wall": (
        "A top-down tile: solid wall section " + _GREEN_BG + _FLAT_VIEW +
        "Reinforced metal wall panel with rivets and seams. "
        "Darker than floor. Gray with structural detail. Impassable. " + _ICON_STYLE
    ),
    "door_closed": (
        "A top-down tile: a closed sliding door " + _GREEN_BG + _FLAT_VIEW +
        "Horizontal seam in center showing closed door halves. "
        "Red indicator light. Metal frame. Door sealed shut. " + _ICON_STYLE
    ),
    "door_open": (
        "A top-down tile: an open doorway " + _GREEN_BG + _FLAT_VIEW +
        "Door halves retracted to sides. Green indicator light. "
        "Metal frame with dark floor visible through opening. " + _ICON_STYLE
    ),
    "exit": (
        "A top-down tile: an exit marker on floor " + _GREEN_BG + _FLAT_VIEW +
        "Metal floor with bright green exit arrow or chevron painted on. "
        "Clearly marked escape route. Green accent on dark floor. " + _ICON_STYLE
    ),
    "entrance": (
        "A top-down tile: an entry point marker " + _GREEN_BG + _FLAT_VIEW +
        "Metal floor with blue entry circle or marker painted on. "
        "Landing/spawn point indicator. Blue accent on dark floor. " + _ICON_STYLE
    ),
    "noisy_floor": (
        "A top-down tile: loose metal floor grating " + _GREEN_BG + _FLAT_VIEW +
        "Damaged rattling floor panel, slightly raised edges. "
        "Warning orange marks at corners. Looks unstable, noisy. " + _ICON_STYLE
    ),
    "terminal": (
        "A top-down tile: data terminal on floor " + _GREEN_BG + _FLAT_VIEW +
        "Small computer console embedded in floor panel. Glowing cyan screen. "
        "Metal base with holographic display. Interactive data terminal. " + _ICON_STYLE
    ),
    "hazard": (
        "A top-down tile: environmental hazard floor " + _GREEN_BG + _FLAT_VIEW +
        "Exposed electrical conduit or plasma leak on damaged floor. "
        "Orange-red glow. Warning stripes. Dangerous to walk on. " + _ICON_STYLE
    ),
    "vent": (
        "A top-down tile: steam vent grate " + _GREEN_BG + _FLAT_VIEW +
        "Large metal grate with steam billowing upward. Gray-blue pipes. "
        "Blocks vision. Industrial ventilation shaft cover. " + _ICON_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Ground Characters (16x16) — player + enemies
# ---------------------------------------------------------------------------

_CHAR_STYLE = (
    "Style: 16-bit SNES-era pixel art, limited color palette, "
    "clean 1px dark outlines. Top-down character sprite viewed from above. "
    "Single centered figure, large bright green margin around it. "
    "Strong silhouette with large color blocks. No fine detail. "
    "No text, no label, no frame, no shadow, no ground, no UI elements."
)

GROUND_PLAYER_PROMPTS: dict[str, str] = {
    "player": (
        "A top-down pixel art character: space trader pilot " + _GREEN_BG + _FLAT_VIEW +
        "Bright blue-accented flight suit, visible shoulders and head from above. "
        "Confident stance, recognizable protagonist. Blue and silver colors. "
        "Clear bright silhouette that stands out against dark backgrounds. " + _CHAR_STYLE
    ),
}

GROUND_ENEMY_PROMPTS: dict[str, str] = {
    "guild_security": (
        "A top-down pixel art character: corporate security guard " + _GREEN_BG + _FLAT_VIEW +
        "Gold and navy blue armored uniform. Professional military stance. "
        "Gold shoulder pads, dark blue body armor. Helmet visible from above. " + _CHAR_STYLE
    ),
    "union_worker": (
        "A top-down pixel art character: mining worker " + _GREEN_BG + _FLAT_VIEW +
        "Rust-orange and brown work coveralls. Hard hat visible from above. "
        "Tool belt, sturdy build. Working class, industrial look. Yellow accents. " + _CHAR_STYLE
    ),
    "pirate_thug": (
        "A top-down pixel art character: space pirate thug " + _GREEN_BG + _FLAT_VIEW +
        "Dark clothing with crimson red accents. Menacing, bulky figure. "
        "Dark charcoal and deep red colors. Aggressive stance. " + _CHAR_STYLE
    ),
    "collective_drone": (
        "A top-down pixel art robot: hovering science drone " + _GREEN_BG + _FLAT_VIEW +
        "Octagonal metallic body, steel gray with teal sensor lights. "
        "Robotic, no legs — hovers. Green central eye sensor. Mechanical. " + _CHAR_STYLE
    ),
    "alliance_scrapper": (
        "A top-down pixel art character: frontier scrapper " + _GREEN_BG + _FLAT_VIEW +
        "Green and tan field gear, utility vest with pockets. "
        "Rugged frontier survivalist look. Brown boots, green jacket. " + _CHAR_STYLE
    ),
    "elite_guard": (
        "A top-down pixel art character: elite heavy guard " + _GREEN_BG + _FLAT_VIEW +
        "Heavy gold and red ceremonial armor. Imposing large shoulders. "
        "Gold visor helmet, red body armor. Most armored figure. " + _CHAR_STYLE
    ),
    "station_sentry": (
        "A top-down pixel art robot: automated turret sentry " + _GREEN_BG + _FLAT_VIEW +
        "Square steel base with gun barrel pointing upward. "
        "Red warning light in center. Gray metal, mechanical. Not humanoid. " + _CHAR_STYLE
    ),
    "crimson_enforcer": (
        "A top-down pixel art character: sinister enforcer " + _GREEN_BG + _FLAT_VIEW +
        "Deep crimson red armor with purple accents. Toxic green visor glowing. "
        "Menacing, intimidating figure. Dark and dangerous appearance. " + _CHAR_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Skill Tree Icons (16x16)
# ---------------------------------------------------------------------------

SKILL_ICON_SIZE = (16, 16)
SKILL_ICON_PROMPTS: dict[str, str] = {
    # Trading Mastery
    "negotiator": (
        "A small icon: two people shaking hands " + _GREEN_BG + _FLAT_VIEW +
        "Handshake deal symbol. Gold and blue colors. " + _ICON_STYLE
    ),
    "market_eye": (
        "A small icon: an eye with a gold coin reflection " + _GREEN_BG + _FLAT_VIEW +
        "All-seeing market eye. Blue eye with gold glint. " + _ICON_STYLE
    ),
    "bulk_trader": (
        "A small icon: stacked cargo crates " + _GREEN_BG + _FLAT_VIEW +
        "Multiple boxes stacked together. Brown crates, large quantity. " + _ICON_STYLE
    ),
    "trade_network": (
        "A small icon: connected nodes in a network " + _GREEN_BG + _FLAT_VIEW +
        "Three dots connected by lines forming a trade network. Blue lines. " + _ICON_STYLE
    ),
    "market_insider": (
        "A small icon: a scroll with a gold seal " + _GREEN_BG + _FLAT_VIEW +
        "Secret market intelligence document. Parchment with gold wax seal. " + _ICON_STYLE
    ),
    # Resource Gathering
    "efficient_drills": (
        "A small icon: a mining drill bit " + _GREEN_BG + _FLAT_VIEW +
        "Sharp spinning drill head. Steel gray with orange sparks. " + _ICON_STYLE
    ),
    "keen_scanner": (
        "A small icon: a radar scanner dish " + _GREEN_BG + _FLAT_VIEW +
        "Small radar dish emitting scan waves. Blue scan lines. " + _ICON_STYLE
    ),
    "rich_veins": (
        "A small icon: glowing crystal ore vein " + _GREEN_BG + _FLAT_VIEW +
        "Cracked rock with bright crystal ore visible inside. Purple crystal. " + _ICON_STYLE
    ),
    "master_extractor": (
        "A small icon: a pickaxe with a gem " + _GREEN_BG + _FLAT_VIEW +
        "Pickaxe striking a gemstone. Steel pickaxe, bright gem. " + _ICON_STYLE
    ),
    "refining_knowledge": (
        "A small icon: a crucible with molten metal " + _GREEN_BG + _FLAT_VIEW +
        "Small smelting crucible with orange molten glow. " + _ICON_STYLE
    ),
    "efficient_refining": (
        "A small icon: a gear with an up arrow " + _GREEN_BG + _FLAT_VIEW +
        "Mechanical gear with efficiency arrow pointing up. Steel and green. " + _ICON_STYLE
    ),
    "yield_mastery": (
        "A small icon: overflowing treasure chest " + _GREEN_BG + _FLAT_VIEW +
        "Small chest overflowing with gems and ore. Gold and jewel colors. " + _ICON_STYLE
    ),
    # Mining Mastery
    "click_power": (
        "A small icon: a fist striking downward " + _GREEN_BG + _FLAT_VIEW +
        "Powerful fist punch impact. Orange impact sparks. " + _ICON_STYLE
    ),
    "passive_drill": (
        "A small icon: an automated drill machine " + _GREEN_BG + _FLAT_VIEW +
        "Self-operating drill with clockwork gears. Steel and bronze. " + _ICON_STYLE
    ),
    "deep_scan": (
        "A small icon: sonar pulse rings " + _GREEN_BG + _FLAT_VIEW +
        "Concentric scan rings expanding outward. Blue sonar waves. " + _ICON_STYLE
    ),
    "drone_bay_1": (
        "A small icon: a single small drone " + _GREEN_BG + _FLAT_VIEW +
        "One small mining drone with blue lights. Compact robot. " + _ICON_STYLE
    ),
    "drone_bay_2": (
        "A small icon: two small drones " + _GREEN_BG + _FLAT_VIEW +
        "Two mining drones flying together. Blue lights, paired. " + _ICON_STYLE
    ),
    "drone_bay_3": (
        "A small icon: three small drones in formation " + _GREEN_BG + _FLAT_VIEW +
        "Three mining drones in triangle formation. Blue lights. " + _ICON_STYLE
    ),
    "drone_efficiency": (
        "A small icon: a drone with a wrench " + _GREEN_BG + _FLAT_VIEW +
        "Upgraded drone with efficiency wrench symbol. Blue and steel. " + _ICON_STYLE
    ),
    "ore_targeting": (
        "A small icon: crosshair on a rock " + _GREEN_BG + _FLAT_VIEW +
        "Targeting reticle focused on ore deposit. Red crosshair. " + _ICON_STYLE
    ),
    "chain_reaction": (
        "A small icon: explosion with chain links " + _GREEN_BG + _FLAT_VIEW +
        "Small explosion with radiating blast waves. Orange and yellow. " + _ICON_STYLE
    ),
    # Leadership & Operations
    "crew_manager": (
        "A small icon: a clipboard with crew roster " + _GREEN_BG + _FLAT_VIEW +
        "Clipboard with list of names. Blue and white, organized. " + _ICON_STYLE
    ),
    "diplomatic_relations": (
        "A small icon: a dove with an olive branch " + _GREEN_BG + _FLAT_VIEW +
        "Peace dove carrying branch. White bird, green branch. " + _ICON_STYLE
    ),
    "inspiring_leader": (
        "A small icon: a raised banner flag " + _GREEN_BG + _FLAT_VIEW +
        "Waving command banner on flagpole. Blue flag, gold trim. " + _ICON_STYLE
    ),
    "tariff_negotiation": (
        "A small icon: a balance scale with coins " + _GREEN_BG + _FLAT_VIEW +
        "Trading balance scale with gold coins. Fair trade symbol. " + _ICON_STYLE
    ),
    "crew_mentor": (
        "A small icon: a book with a star " + _GREEN_BG + _FLAT_VIEW +
        "Open book with glowing star above it. Knowledge and guidance. " + _ICON_STYLE
    ),
    # Social Arts
    "silver_tongue": (
        "A small icon: a silver speech bubble " + _GREEN_BG + _FLAT_VIEW +
        "Shiny silver speech bubble with sparkle. Persuasive words. " + _ICON_STYLE
    ),
    "commanding_presence": (
        "A small icon: a crown or command star " + _GREEN_BG + _FLAT_VIEW +
        "Gold command star radiating authority aura. Leadership symbol. " + _ICON_STYLE
    ),
    "keen_insight": (
        "A small icon: a glowing third eye " + _GREEN_BG + _FLAT_VIEW +
        "Mystical eye glowing with blue perception light. Wisdom symbol. " + _ICON_STYLE
    ),
    # Ground Combat
    "scrapper": (
        "A small icon: crossed fists " + _GREEN_BG + _FLAT_VIEW +
        "Two fists crossed in combat stance. Strong fighter symbol. " + _ICON_STYLE
    ),
    "tough_hide": (
        "A small icon: a shield with armor plates " + _GREEN_BG + _FLAT_VIEW +
        "Heavy metal shield with rivets. Steel gray, tough defense. " + _ICON_STYLE
    ),
    "quick_reflexes": (
        "A small icon: a lightning bolt " + _GREEN_BG + _FLAT_VIEW +
        "Fast yellow lightning bolt. Speed and agility symbol. " + _ICON_STYLE
    ),
    "intimidating_presence": (
        "A small icon: a skull with red eyes " + _GREEN_BG + _FLAT_VIEW +
        "Menacing skull with glowing red eyes. Fear and intimidation. " + _ICON_STYLE
    ),
    "last_stand": (
        "A small icon: a broken sword standing upright " + _GREEN_BG + _FLAT_VIEW +
        "Broken blade thrust into ground. Final defiance, never give up. " + _ICON_STYLE
    ),
    "veteran": (
        "A small icon: a medal with star " + _GREEN_BG + _FLAT_VIEW +
        "Military medal of honor with gold star. Battle experience. " + _ICON_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category: Station Hub Location Icons (16x16)
# ---------------------------------------------------------------------------

HUB_ICON_SIZE = (16, 16)
HUB_ICON_PROMPTS: dict[str, str] = {
    "market": (
        "A small icon: a market stall or shop " + _GREEN_BG + _FLAT_VIEW +
        "Trading market stand with goods. Gold coins and crates. " + _ICON_STYLE
    ),
    "cantina": (
        "A small icon: a drinking glass or mug " + _GREEN_BG + _FLAT_VIEW +
        "Space bar drink in a futuristic glass. Blue liquid glowing. " + _ICON_STYLE
    ),
    "repair_bay": (
        "A small icon: a wrench and gear " + _GREEN_BG + _FLAT_VIEW +
        "Repair wrench crossing a mechanical gear. Steel and orange. " + _ICON_STYLE
    ),
    "mining": (
        "A small icon: a pickaxe on rock " + _GREEN_BG + _FLAT_VIEW +
        "Mining pickaxe embedded in asteroid rock. Gray and orange sparks. " + _ICON_STYLE
    ),
    "salvaging": (
        "A small icon: a magnet pulling scrap " + _GREEN_BG + _FLAT_VIEW +
        "Magnetic salvage claw grabbing metal debris. Red magnet, gray scrap. " + _ICON_STYLE
    ),
    "refining": (
        "A small icon: a furnace or smelter " + _GREEN_BG + _FLAT_VIEW +
        "Small refining furnace with molten metal glow. Orange and steel. " + _ICON_STYLE
    ),
    "shipyard": (
        "A small icon: a ship hull frame " + _GREEN_BG + _FLAT_VIEW +
        "Ship under construction, wireframe hull skeleton. Blue and steel. " + _ICON_STYLE
    ),
    "unique": (
        "A small icon: a glowing star or diamond " + _GREEN_BG + _FLAT_VIEW +
        "Special rare glowing diamond or star. Bright gold with sparkle. " + _ICON_STYLE
    ),
}

# ---------------------------------------------------------------------------
# Category registry
# ---------------------------------------------------------------------------
# Auto-expand prompts for upgrades that don't have hand-crafted entries
# ---------------------------------------------------------------------------

_UPGRADE_CATEGORY_COLORS = {
    "weapon": "red-orange",
    "defense": "blue",
    "shield": "light blue",
    "engine": "orange",
    "utility": "green",
    "cargo": "brown",
    "reactor": "yellow-gold",
    "fuel": "gray-blue",
    "crew": "warm amber",
}


def _expand_portrait_prompts() -> None:
    """Add auto-generated prompts for NPCs missing from the hand-crafted dict."""
    npcs_path = PROJECT_ROOT / "data" / "characters" / "npcs.json"
    if not npcs_path.exists():
        return
    with open(npcs_path) as f:
        data = json.load(f)
    _faction_clothing = {
        "nexus_trade": "gold-trimmed merchant clothing",
        "forgeworks_industrial": "orange-accented industrial work gear",
        "free_salvagers": "teal-accented salvager outfit",
        "axiom_research": "blue-white research uniform",
        "": "neutral spacer jumpsuit",
    }
    for npc in data.get("npcs", []):
        nid = npc["id"]
        if nid in PORTRAIT_PROMPTS:
            continue
        name = npc.get("name", nid.replace("_", " ").title())
        title = npc.get("title", "spacer")
        faction = npc.get("faction_id", "")
        clothing = _faction_clothing.get(faction, _faction_clothing[""])
        PORTRAIT_PROMPTS[nid] = (
            f"Pixel art character portrait: {name}, {title}. "
            f"Wearing {clothing}. "
            f"Dark space station background. " + _BUST_VIEW + _PORTRAIT_STYLE
        )


_expand_portrait_prompts()


def _expand_upgrade_prompts() -> None:
    """Add auto-generated prompts for upgrades missing from the hand-crafted dict."""
    upgrades_path = PROJECT_ROOT / "data" / "ships" / "upgrades.json"
    if not upgrades_path.exists():
        return
    with open(upgrades_path) as f:
        data = json.load(f)
    for upgrade in data.get("upgrades", []):
        uid = upgrade["id"]
        if uid in UPGRADE_PROMPTS:
            continue
        name = upgrade.get("name", uid.replace("_", " ").title())
        category = upgrade.get("slot_type", upgrade.get("category", "misc"))
        color = _UPGRADE_CATEGORY_COLORS.get(category, "silver-gray")
        UPGRADE_PROMPTS[uid] = (
            f"A small utility icon: {name} " + _GREEN_BG + _FLAT_VIEW +
            f"A {category} upgrade for a spaceship. {color.title()} color scheme. "
            f"Simple iconic pixel art symbol representing {name.lower()}. " + _ICON_STYLE
        )


_expand_upgrade_prompts()

# ---------------------------------------------------------------------------

CATEGORIES: dict[str, dict] = {
    "emblems": {
        "prompts": EMBLEM_PROMPTS,
        "size": EMBLEM_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/factions",
        "description": "Faction emblems (24x24)",
    },
    "ships_player": {
        "prompts": PLAYER_SHIP_PROMPTS,
        "size": SHIP_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ships/player",
        "description": "Player ship sprites (32x32)",
    },
    "ships_enemy": {
        "prompts": ENEMY_SHIP_PROMPTS,
        "size": SHIP_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ships/enemies",
        "description": "Enemy ship base sprites (32x32)",
    },
    "portraits": {
        "prompts": PORTRAIT_PROMPTS,
        "size": PORTRAIT_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/portraits",
        "description": "NPC portrait sprites (50x60)",
        "has_green_bg": False,  # Portraits use dark bg, not green screen
    },
    "upgrades": {
        "prompts": UPGRADE_PROMPTS,
        "size": UPGRADE_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/upgrades",
        "description": "Upgrade icons (16x16)",
    },
    "mining_rocks": {
        "prompts": MINING_ROCK_PROMPTS,
        "size": MINING_ROCK_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/mining",
        "description": "Mining rock sprites (32x32)",
    },
    "salvage_cells": {
        "prompts": SALVAGE_CELL_PROMPTS,
        "size": SALVAGE_CELL_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/salvage",
        "description": "Salvage cell & quality frame sprites (32x32 / 20x20 / 16x16)",
    },
    "salvage_bgs": {
        "prompts": SALVAGE_BG_PROMPTS,
        "size": SALVAGE_BG_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/salvage",
        "description": "Derelict background illustrations (160x120)",
        "has_green_bg": False,
    },
    "ground_tiles": {
        "prompts": GROUND_TILE_PROMPTS,
        "size": GROUND_TILE_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ground_tiles/neutral",
        "description": "Ground tile sprites (16x16)",
    },
    "ground_player": {
        "prompts": GROUND_PLAYER_PROMPTS,
        "size": GROUND_TILE_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ground_tiles",
        "description": "Ground player character (16x16)",
    },
    "ground_enemies": {
        "prompts": GROUND_ENEMY_PROMPTS,
        "size": GROUND_TILE_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ground_tiles/enemies",
        "description": "Ground enemy characters (16x16)",
    },
    "skill_icons": {
        "prompts": SKILL_ICON_PROMPTS,
        "size": SKILL_ICON_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ui/skills",
        "description": "Skill tree icons (16x16)",
    },
    "hub_icons": {
        "prompts": HUB_ICON_PROMPTS,
        "size": HUB_ICON_SIZE,
        "palette": "master_palette",
        "output_subdir": "sprites/ui/location_types",
        "description": "Station hub location icons (16x16)",
    },
}

# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------


def _generate_image_dalle(client: OpenAI, prompt: str) -> Image.Image:
    """Generate a raw image via DALL-E 3."""
    import httpx

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    image_url = response.data[0].url
    resp = httpx.get(image_url, timeout=30.0)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGBA")


def _generate_image_gemini(api_key: str, prompt: str) -> Image.Image:
    """Generate a raw image via Google Imagen 4.0."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Try Imagen 4.0 first (purpose-built image generation)
    try:
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            import io
            return Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    except Exception as e:
        print(f"    [Imagen 4.0] Failed: {e}, falling back to Gemini Flash...")

    # Fallback: Gemini 2.5 Flash with image output
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                import io
                return Image.open(io.BytesIO(part.inline_data.data)).convert("RGBA")
    raise RuntimeError("No image returned from Gemini")


def assemble_sprite_sheet(base_frame: Image.Image, num_frames: int = 6) -> Image.Image:
    """Create a 6-frame sprite sheet from a single base frame.

    Generates subtle idle animation by varying brightness/glow across frames.
    Frame pattern: base → brighter → brightest → base → dimmer → dimmest
    This creates a pulsing engine/light effect when looped.

    Args:
        base_frame: Single RGBA sprite frame.
        num_frames: Number of frames (default 6).

    Returns:
        Horizontal sprite sheet (num_frames * width, height).
    """
    from PIL import ImageEnhance

    w, h = base_frame.size
    sheet = Image.new("RGBA", (w * num_frames, h), (0, 0, 0, 0))

    # Brightness multipliers for a subtle pulse cycle
    brightness_cycle = [1.0, 1.06, 1.12, 1.0, 0.94, 0.88]

    for i in range(num_frames):
        frame = base_frame.copy()
        # Apply subtle brightness variation (only to non-transparent pixels)
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(brightness_cycle[i % len(brightness_cycle)])
        # Preserve original alpha channel
        _, _, _, alpha = base_frame.split()
        frame.putalpha(alpha)
        sheet.paste(frame, (i * w, 0))

    return sheet


def generate_and_process(
    client,
    asset_id: str,
    prompt: str,
    size: tuple[int, int],
    palette: list[tuple[int, int, int]],
    output_dir: pathlib.Path,
    has_green_bg: bool = True,
    backend: str = "openai",
    gemini_key: str = "",
) -> bool:
    """Generate one sprite end-to-end via DALL-E 3 or Gemini + pixel pipeline.

    Args:
        client: OpenAI client (used when backend="openai").
        asset_id: Filename stem (e.g., "shuttle").
        prompt: Generation prompt text.
        size: Target sprite (width, height).
        palette: RGB palette for quantization.
        output_dir: Directory for output files.
        has_green_bg: Whether the prompt uses green screen bg (True for most).
        backend: "openai" or "gemini".
        gemini_key: Gemini API key (used when backend="gemini").

    Returns:
        True on success, False on failure.
    """
    try:
        if backend == "gemini":
            raw = _generate_image_gemini(gemini_key, prompt)
        else:
            raw = _generate_image_dalle(client, prompt)

        # Save raw for future reprocessing
        raw.save(str(output_dir / f"{asset_id}_raw.png"))

        if has_green_bg:
            # Full pipeline: bg removal → clean alpha → resize → quantize → outline
            result = process_sprite(
                raw, size, palette,
                outline_color=OUTLINE_COLOR,
                intermediate_scale=2,
            )
        else:
            # Portraits: dark background, skip green-screen removal
            # Manual bg handling: just resize + quantize + outline
            from tools.pixel_pipeline import (
                resize_for_pixel_art, clean_alpha, quantize_to_palette,
                enforce_outline,
            )
            result = resize_for_pixel_art(raw, size, intermediate_scale=2)
            result = clean_alpha(result)
            result = quantize_to_palette(result, palette)
            # No outline for portraits (they fill the frame)

        result.save(str(output_dir / f"{asset_id}.png"))

        # For ship categories: also assemble a 6-frame sprite sheet
        if size == SHIP_SIZE:
            sheet = assemble_sprite_sheet(result, num_frames=6)
            sheet_path = output_dir / f"{asset_id}_sheet.png"
            sheet.save(str(sheet_path))
            print(f"    Sheet: {sheet_path.name} ({sheet.size[0]}x{sheet.size[1]})")

        return True

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate game sprites via DALL-E 3 or Gemini + pixel pipeline."
    )
    parser.add_argument(
        "category",
        choices=list(CATEGORIES.keys()),
        help="Asset category to generate",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        help="Generate only specific asset IDs",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List asset IDs for this category and exit",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip assets that already have a .png",
    )
    parser.add_argument(
        "--backend",
        choices=["openai", "gemini"],
        default="gemini",
        help="Image generation backend (default: gemini for higher quality)",
    )
    args = parser.parse_args()

    cat = CATEGORIES[args.category]
    prompts = cat["prompts"]

    if args.list:
        print(f"\n{cat['description']}:")
        for aid in sorted(prompts.keys()):
            print(f"  {aid}")
        print(f"\n{len(prompts)} assets total.")
        return

    load_dotenv()
    import os

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    client = None
    if args.backend == "openai":
        client = OpenAI()
    elif not gemini_key:
        print("ERROR: GEMINI_API_KEY not set. Use --backend openai or set the key.")
        sys.exit(1)

    palette = load_palette(cat["palette"])
    output_dir = ASSETS_BASE / cat["output_subdir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    has_green_bg = cat.get("has_green_bg", True)

    # Determine targets
    if args.only:
        targets = args.only
        unknown = [t for t in targets if t not in prompts]
        if unknown:
            print(f"Unknown asset IDs: {unknown}")
            print(f"Use --list to see available IDs.")
            sys.exit(1)
    else:
        targets = list(prompts.keys())

    if args.skip_existing:
        targets = [t for t in targets if not (output_dir / f"{t}.png").exists()]
        if not targets:
            print("All assets already generated. Nothing to do.")
            return

    est_cost = len(targets) * 0.04
    print(f"\n{cat['description']}")
    print(f"Generating {len(targets)} sprites...")
    print(f"Output: {output_dir}")
    print(f"Palette: {len(palette)} colors")
    print(f"Target size: {cat['size'][0]}x{cat['size'][1]}")
    print(f"Estimated cost: ~${est_cost:.2f}")
    print()

    succeeded = 0
    failed = []

    for i, aid in enumerate(targets, 1):
        prompt = prompts[aid]
        print(f"[{i}/{len(targets)}] {aid}...")

        ok = generate_and_process(
            client, aid, prompt,
            cat["size"], palette, output_dir,
            has_green_bg=has_green_bg,
            backend=args.backend,
            gemini_key=gemini_key,
        )
        if ok:
            succeeded += 1
            print(f"    OK")
        else:
            failed.append(aid)
            print(f"    FAILED")

        if i < len(targets):
            time.sleep(1)

    print(f"\n{'=' * 40}")
    print(f"Done: {succeeded}/{len(targets)} succeeded")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        print(f"Re-run with: python tools/generate_sprites.py {args.category} --only {' '.join(failed)}")


if __name__ == "__main__":
    main()
