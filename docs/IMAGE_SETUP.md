# Image Asset Setup Guide

This guide explains how to add the 32-bit pixel art images to your Space Trader game.

## Overview

The game now supports custom 32-bit pixel art backgrounds and system images. Images are **optional** - the game will gracefully fall back to procedural rendering if images are not present.

## Directory Structure

```
spacegame/data/assets/images/
├── backgrounds/
│   ├── starfield.png         (Main menu background)
│   ├── deep_space.png        (Galaxy map option 1)
│   ├── nebula.png            (Galaxy map option 2)
│   ├── trade_routes.png      (Galaxy map option 3)
│   └── frontier.png          (Galaxy map option 4)
└── systems/
    ├── nexus_prime.png       (Trade hub system)
    ├── verdant.png           (Agricultural world)
    ├── forgeworks.png        (Industrial planet)
    ├── breakstone.png        (Mining frontier)
    └── axiom_labs.png        (Research station)
```

## Image Specifications

### Background Images (5 total)
- **Resolution**: 1280x720 pixels (16:9 aspect ratio)
- **Format**: PNG
- **Usage**: Full-screen backgrounds for main menu and galaxy map
- **Note**: Galaxy map picks one randomly each time you view it

### System Images (5 total)
- **Display Size**: 280x150 pixels
- **Format**: PNG
- **Usage**: Displayed in the system info panel on galaxy map
- **Naming**: Must match system IDs from `data/galaxy/systems.json`

## Midjourney Prompts (With Style Reference)

All images should use this style reference for consistency:
```
--sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

### Background Images

**starfield.png** (Main Menu)
```
Clean star field background with thousands of white and blue stars on pure black space, varying star brightness and sizes, simple and professional, suitable for UI overlay, 32-bit pixel art, SNES era graphics, pixel perfect stars, minimal dithering, retro video game --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**deep_space.png**
```
Deep space starfield background with distant galaxies, subtle purple and blue nebula clouds, scattered white stars of varying brightness, vast empty darkness, peaceful infinite space, 32-bit pixel art, SNES era graphics, dithered nebula clouds, pixel perfect stars, retro video game background --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**nebula.png**
```
Colorful space nebula with swirling cosmic dust in blues purples and pinks, scattered star clusters, ethereal cloud formations, mystical sci-fi atmosphere, 32-bit pixel art, SNES era graphics, dithered gradients, pixel perfect stars, retro video game space background --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**trade_routes.png**
```
Busy sector of space with distant ship light trails, faint navigation beacon lights, subtle asteroid clusters in distance, well-traveled trade route aesthetic, safe civilized space, 32-bit pixel art, SNES era graphics, dark blue-black with subtle activity, dithered effects, retro game background --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**frontier.png**
```
Darker dangerous space sector with denser asteroid fields in distance, ominous red-orange nebula glow, fewer stars, isolated lawless frontier aesthetic, subtle sense of danger, 32-bit pixel art, SNES era graphics, dithered danger glow, pixel art asteroids, retro game background --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

### System Images

**nexus_prime.png** (Trade Hub)
```
Massive circular space station trade hub at center of converging routes, gleaming chrome architecture, countless docking bays, holographic advertisements, bright blue neon lighting, bustling commercial spaceport viewed from space, 32-bit pixel art, SNES era graphics, dithered gradients, clean pixel work, retro video game aesthetic, dark blue-black space background, bright cyan highlights --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**verdant.png** (Agricultural World)
```
Lush green agricultural planet with geometric farm sectors visible from orbit, massive hydroponic towers reaching into atmosphere, hexagonal emerald field patterns, transparent biodomes scattered across continents, peaceful organic sci-fi aesthetic, 32-bit pixel art, SNES era graphics, vibrant greens and earth tones, dithered shading, clean pixel work, retro video game --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**forgeworks.png** (Industrial Planet)
```
Dark industrial planet covered in towering factories and orbital shipyards constructing starships, molten metal rivers, glowing forges, orange and red lighting, smokestacks with emissions, heavy industry with sparks and welding, gritty steel aesthetic, 32-bit pixel art, SNES era graphics, dark grays and burning oranges, dithered fire effects, retro game art --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**breakstone.png** (Mining Frontier)
```
Chaotic asteroid field with rough mining station carved into largest asteroid, exposed mineral veins glowing various colors, makeshift salvaged structures, dim harsh lighting, dangerous frontier outpost, ships navigating debris, rust and weathering, lawless wild west in space, 32-bit pixel art, SNES era graphics, browns grays with mineral color highlights, dithered rock textures --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

**axiom_labs.png** (Research Station)
```
Pristine white and chrome research facilities orbiting untouched Earth-like planet, elegant curved architecture, scanning arrays and telescopes, clean sterile aesthetic, soft blue-white lighting, advanced gleaming technology, transparent observation laboratories, peaceful isolated location, 32-bit pixel art, SNES era graphics, whites blues and subtle purples, dithered glows, pixel perfect --ar 16:9 --v 6 --sref https://cdn.midjourney.com/2c5c4343-9b19-41b5-b3b7-eddfd9a1feeb/0_2.png --sw 100
```

## Installation Steps

1. **Generate images** using Midjourney with the prompts above
2. **Download images** from Midjourney (1280x720 PNG format)
3. **Rename files** to match the names listed above
4. **Place files** in the appropriate directories:
   - Backgrounds → `spacegame/data/assets/images/backgrounds/`
   - Systems → `spacegame/data/assets/images/systems/`
5. **Run the game** - images will be loaded automatically!

## Testing

The game will log image loading status:
- **Success**: `[INFO] Loaded galaxy map background: nebula`
- **Missing**: `[WARNING] Image not found: ...` (game continues with fallback)

Check the console output when launching the game to verify images are loading correctly.

## Tips

- Images are cached after first load for performance
- Galaxy map background is randomly selected each time
- System images are loaded on-demand when viewing a system
- Missing images don't cause errors - the game uses fallback rendering

## Art Style Notes

**32-bit pixel art aesthetic** inspired by:
- SNES era graphics (Star Control 2, Elite)
- Dithered gradients for smooth color transitions
- Limited color palette with bright cyan highlights (#64C8FF)
- Dark blue-black backgrounds (#0A0A14)
- Clean pixel work with retro charm
