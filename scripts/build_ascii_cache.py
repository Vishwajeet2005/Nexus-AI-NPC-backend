import os
import sys

sys.path.insert(0, os.path.abspath("."))
from scripts.convert_to_ascii import convert_face_to_ascii_grid, render_ascii_grid

PORTRAITS_PATHS = {
    "cooperative": "api/data/portraits/marcus_cooperative.jpg",
    "deflecting":  "api/data/portraits/marcus_deflecting.jpg",
    "nervous":     "api/data/portraits/marcus_nervous.jpg",
    "hostile":     "api/data/portraits/marcus_hostile.jpg",
    "confessing":  "api/data/portraits/marcus_confess.jpg",
}

output_path = "api/data/portraits/ascii_cache.py"
ascii_grids = {}

for emotion, img_path in PORTRAITS_PATHS.items():
    if os.path.exists(img_path):
        print(f"Building fine ASCII grid for {emotion} from {img_path}...")
        ascii_grids[emotion] = convert_face_to_ascii_grid(img_path, emotion, width=46)
    else:
        print(f"Warning: {img_path} not found!")

# Ensure all grids have the same rows and columns for morphing
target_h = max(len(g) for g in ascii_grids.values())
target_w = 46

for emotion, grid in ascii_grids.items():
    # If any grid has fewer rows, pad with empty rows at the bottom
    while len(grid) < target_h:
        grid.append([(0, 0, 0, " ") for _ in range(target_w)])

with open(output_path, "w", encoding="utf-8") as f:
    f.write('"""\n')
    f.write('api/data/portraits/ascii_cache.py\n')
    f.write('──────────────────────────────────\n')
    f.write('Pre-computed fine-character ANSI TrueColor ASCII portraits and in-place morphing engine for Marcus Webb.\n')
    f.write('Features:\n')
    f.write('  - Pure ASCII text typography (no chunky half-block pixels, native terminal background).\n')
    f.write(f'  - Compact dimensions ({target_w} cols × {target_h} rows) designed for single-image in-place display.\n')
    f.write('  - High-dynamic-range face framing with clear facial features (eyes, eyebrows, mouth, expressions).\n')
    f.write('  - In-place TrueColor 8x8 Bayer dithered morph transitions.\n')
    f.write('"""\n\n')
    f.write('import asyncio\n')
    f.write('import math\n')
    f.write('import os\n')
    f.write('import sys\n\n')
    
    f.write('# Enable ANSI and UTF-8 on Windows consoles\n')
    f.write('if sys.platform == "win32":\n')
    f.write('    try:\n')
    f.write('        os.system("")\n')
    f.write('        sys.stdout.reconfigure(encoding="utf-8")\n')
    f.write('    except Exception:\n')
    f.write('        pass\n\n')
    
    f.write('# 8x8 Bayer dithering matrix for smooth spatial dissolving during morphs\n')
    f.write('BAYER_8X8 = [\n')
    f.write('    [ 0/64, 32/64,  8/64, 40/64,  2/64, 34/64, 10/64, 42/64],\n')
    f.write('    [48/64, 16/64, 56/64, 24/64, 50/64, 18/64, 58/64, 26/64],\n')
    f.write('    [12/64, 44/64,  4/64, 36/64, 14/64, 46/64,  6/64, 38/64],\n')
    f.write('    [60/64, 28/64, 52/64, 20/64, 62/64, 30/64, 54/64, 22/64],\n')
    f.write('    [ 3/64, 35/64, 11/64, 43/64,  1/64, 33/64,  9/64, 41/64],\n')
    f.write('    [51/64, 19/64, 59/64, 27/64, 49/64, 17/64, 57/64, 25/64],\n')
    f.write('    [15/64, 47/64,  7/64, 39/64, 13/64, 45/64,  5/64, 37/64],\n')
    f.write('    [63/64, 31/64, 55/64, 23/64, 61/64, 29/64, 53/64, 21/64],\n')
    f.write(']\n\n')
    
    f.write('def _normalize_behaviour(behaviour) -> str:\n')
    f.write('    name = str(getattr(behaviour, "value", behaviour)).lower()\n')
    f.write('    if name == "confess":\n')
    f.write('        return "confessing"\n')
    f.write('    return name\n\n')
    
    f.write('def render_ascii_lines(grid) -> list[str]:\n')
    f.write('    """Render a 2D grid of (r, g, b, char) tuples into a list of ANSI TrueColor lines."""\n')
    f.write('    lines = []\n')
    f.write('    for row in grid:\n')
    f.write('        row_chars = []\n')
    f.write('        for r, g, b, c in row:\n')
    f.write('            if c == " ":\n')
    f.write('                row_chars.append(" ")\n')
    f.write('            else:\n')
    f.write('                row_chars.append(f"\\033[38;2;{r};{g};{b}m{c}")\n')
    f.write('        lines.append("".join(row_chars) + "\\033[0m")\n')
    f.write('    return lines\n\n')
    f.write('def render_ascii_grid(grid) -> str:\n')
    f.write('    """Render a 2D grid of (r, g, b, char) tuples into ANSI TrueColor text."""\n')
    f.write('    return "\\n".join(render_ascii_lines(grid))\n\n')
    
    f.write('# 2D pixel grids: dict[emotion, list[list[(r, g, b, char)]]]\n')
    f.write('PORTRAIT_GRIDS = {\n')
    for emotion, grid in ascii_grids.items():
        f.write(f'    "{emotion}": [\n')
        for row in grid:
            f.write(f'        {row!r},\n')
        f.write('    ],\n')
    f.write('}\n\n')
    
    f.write('# Pre-rendered static ANSI string portraits\n')
    f.write('PORTRAIT_LINES = {\n')
    f.write('    k: render_ascii_lines(v) for k, v in PORTRAIT_GRIDS.items()\n')
    f.write('}\n')
    f.write('PORTRAITS = {\n')
    f.write('    k: "\\n".join(v) for k, v in PORTRAIT_LINES.items()\n')
    f.write('}\n\n')
    
    f.write('def get_portrait_lines(behaviour: str) -> list[str]:\n')
    f.write('    """Return the list of static TrueColor ASCII portrait lines for Marcus Webb."""\n')
    f.write('    name = _normalize_behaviour(behaviour)\n')
    f.write('    return PORTRAIT_LINES.get(name) or PORTRAIT_LINES.get("cooperative")\n\n')
    
    f.write('def get_portrait(behaviour: str) -> str:\n')
    f.write('    """Return the static TrueColor ASCII portrait string for Marcus Webb."""\n')
    f.write('    name = _normalize_behaviour(behaviour)\n')
    f.write('    return PORTRAITS.get(name) or PORTRAITS.get("cooperative")\n\n')
    
    f.write('def show_portrait(behaviour: str):\n')
    f.write('    """Print the static TrueColor ASCII portrait for Marcus Webb."""\n')
    f.write('    art = get_portrait(behaviour)\n')
    f.write('    if art:\n')
    f.write('        print(f"\\n{art}")\n\n')
    
    f.write('def set_portrait_style(style: str):\n')
    f.write('    pass  # Fine ASCII is always used\n\n')
    
    f.write('def get_morph_frames(from_behaviour: str, to_behaviour: str, frames: int = 10):\n')
    f.write('    """Yield 2D grids representing intermediate morph frames from from_behaviour to to_behaviour."""\n')
    f.write('    from_name = _normalize_behaviour(from_behaviour)\n')
    f.write('    to_name = _normalize_behaviour(to_behaviour)\n')
    f.write('    grid_a = PORTRAIT_GRIDS.get(from_name) or PORTRAIT_GRIDS.get("cooperative")\n')
    f.write('    grid_b = PORTRAIT_GRIDS.get(to_name) or PORTRAIT_GRIDS.get("cooperative")\n')
    f.write('    if not grid_a or not grid_b or from_name == to_name:\n')
    f.write('        yield grid_b\n')
    f.write('        return\n')
    f.write('    height = len(grid_a)\n')
    f.write('    width = len(grid_a[0])\n')
    f.write('    for f in range(1, frames + 1):\n')
    f.write('        t = f / frames\n')
    f.write('        t_eased = (1.0 - math.cos(t * math.pi)) / 2.0\n')
    f.write('        frame = []\n')
    f.write('        for y in range(height):\n')
    f.write('            row = []\n')
    f.write('            row_a = grid_a[y]\n')
    f.write('            row_b = grid_b[y]\n')
    f.write('            for x in range(width):\n')
    f.write('                ra, ga, ba, ca = row_a[x]\n')
    f.write('                rb, gb, bb, cb = row_b[x]\n')
    f.write('                r = int((1.0 - t_eased) * ra + t_eased * rb)\n')
    f.write('                g = int((1.0 - t_eased) * ga + t_eased * gb)\n')
    f.write('                b = int((1.0 - t_eased) * ba + t_eased * bb)\n')
    f.write('                threshold = BAYER_8X8[y % 8][x % 8]\n')
    f.write('                char = cb if t_eased >= threshold else ca\n')
    f.write('                row.append((r, g, b, char))\n')
    f.write('            frame.append(row)\n')
    f.write('        yield frame\n\n')
    
    f.write('async def morph_portrait(from_behaviour: str, to_behaviour: str, frames: int = 10, delay: float = 0.035):\n')
    f.write('    """Smoothly in-place cross-dissolve between two fine ASCII portraits using Bayer dithering."""\n')
    f.write('    from_name = _normalize_behaviour(from_behaviour)\n')
    f.write('    to_name = _normalize_behaviour(to_behaviour)\n\n')
    f.write('    if not sys.stdout.isatty():\n')
    f.write('        show_portrait(to_name)\n')
    f.write('        return\n\n')
    f.write('    grid_a = PORTRAIT_GRIDS.get(from_name) or PORTRAIT_GRIDS.get("cooperative")\n')
    f.write('    grid_b = PORTRAIT_GRIDS.get(to_name) or PORTRAIT_GRIDS.get("cooperative")\n\n')
    f.write('    if not grid_a or not grid_b or from_name == to_name:\n')
    f.write('        show_portrait(to_name)\n')
    f.write('        return\n\n')
    f.write('    height = len(grid_a)\n')
    f.write('    # Morph frames\n')
    f.write('    for frame in get_morph_frames(from_behaviour, to_behaviour, frames=frames):\n')
    f.write('        sys.stdout.write(f"\\033[{height}A\\r")\n')
    f.write('        sys.stdout.flush()\n')
    f.write('        sys.stdout.write(render_ascii_grid(frame) + "\\n")\n')
    f.write('        sys.stdout.flush()\n')
    f.write('        await asyncio.sleep(delay)\n')

print(f"Successfully generated {output_path}!")
