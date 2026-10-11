import os
import sys

sys.path.insert(0, os.path.abspath("."))
from scripts.convert_to_ascii import convert_face_to_halfblocks, convert_face_to_ascii

PORTRAITS_PATHS = {
    "cooperative": "api/data/portraits/marcus_cooperative.jpg",
    "deflecting":  "api/data/portraits/marcus_deflecting.jpg",
    "nervous":     "api/data/portraits/marcus_nervous.jpg",
    "hostile":     "api/data/portraits/marcus_hostile.jpg",
    "confessing":  "api/data/portraits/marcus_confess.jpg",
}

output_path = "api/data/portraits/ascii_cache.py"

halfblock_grids = {}
ascii_strings = {}

for emotion, img_path in PORTRAITS_PATHS.items():
    if os.path.exists(img_path):
        print(f"Building {emotion} cache from {img_path}...")
        halfblock_grids[emotion] = convert_face_to_halfblocks(img_path, emotion, width=38, height_px=38)
        ascii_strings[emotion] = convert_face_to_ascii(img_path, emotion, width=36, height=18)
    else:
        print(f"Warning: {img_path} not found!")

with open(output_path, "w", encoding="utf-8") as f:
    f.write('"""\n')
    f.write('api/data/portraits/ascii_cache.py\n')
    f.write('──────────────────────────────────\n')
    f.write('High-resolution ANSI TrueColor facial expression portraits and morphing engine for Marcus Webb.\n')
    f.write('Features:\n')
    f.write("  - Micro-character Half-Blocks ('▀'): 2 vertical TrueColor pixels per terminal character cell.\n")
    f.write('  - Compact dimensions (38 cols × 19 rows) ensuring full expression visibility without crowding terminal.\n')
    f.write('  - Tight face framing on eyes, brows, mouth, sweat, and facial wrinkles.\n')
    f.write('  - Smooth in-place cross-dissolve emotion morphing.\n')
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
    
    f.write('ACTIVE_STYLE = "halfblock"\n\n')
    
    f.write('def set_portrait_style(style: str):\n')
    f.write('    global ACTIVE_STYLE\n')
    f.write('    ACTIVE_STYLE = style.lower().strip()\n\n')
    
    f.write('def _normalize_behaviour(behaviour) -> str:\n')
    f.write('    name = str(getattr(behaviour, "value", behaviour)).lower()\n')
    f.write('    if name == "confess":\n')
    f.write('        return "confessing"\n')
    f.write('    return name\n\n')
    
    f.write('def render_halfblock_grid(grid) -> str:\n')
    f.write('    """Format 2D half-block grid into TrueColor ANSI escape strings."""\n')
    f.write('    lines = []\n')
    f.write('    for row in grid:\n')
    f.write('        line = "".join(f"\\033[38;2;{rt};{gt};{bt};48;2;{rb};{gb};{bb}m▀" for rt, gt, bt, rb, gb, bb in row)\n')
    f.write('        lines.append(line + "\\033[0m")\n')
    f.write('    return "\\n".join(lines)\n\n')
    
    f.write('# 2D pixel grids for half-block micro-pixel rendering: dict[emotion, list[list[(rt, gt, bt, rb, gb, bb)]]]\n')
    f.write('PORTRAIT_GRIDS = {\n')
    for emotion, grid in halfblock_grids.items():
        f.write(f'    "{emotion}": [\n')
        for row in grid:
            f.write(f'        {row!r},\n')
        f.write('    ],\n')
    f.write('}\n\n')
    
    f.write('# Pre-computed half-block portraits\n')
    f.write('PORTRAITS_HALFBLOCK = {\n')
    f.write('    k: render_halfblock_grid(v) for k, v in PORTRAIT_GRIDS.items()\n')
    f.write('}\n\n')
    
    f.write('# Pre-computed compact ASCII character portraits\n')
    f.write('PORTRAITS_ASCII = {\n')
    for emotion, art_str in ascii_strings.items():
        f.write(f'    "{emotion}": {art_str!r},\n')
    f.write('}\n\n')
    
    f.write('# Default portrait dictionary referenced by nexus_demo.py\n')
    f.write('PORTRAITS = PORTRAITS_HALFBLOCK\n\n')
    
    f.write('def show_portrait(behaviour: str):\n')
    f.write('    """Print the static portrait for Marcus Webb in the active style."""\n')
    f.write('    name = _normalize_behaviour(behaviour)\n')
    f.write('    if ACTIVE_STYLE == "ascii":\n')
    f.write('        art = PORTRAITS_ASCII.get(name) or PORTRAITS_ASCII.get("cooperative")\n')
    f.write('    else:\n')
    f.write('        art = PORTRAITS_HALFBLOCK.get(name) or PORTRAITS_HALFBLOCK.get("cooperative")\n')
    f.write('    if art:\n')
    f.write('        print(f"\\n{art}")\n\n')
    
    f.write('async def morph_portrait(from_behaviour: str, to_behaviour: str, frames: int = 10, delay: float = 0.035):\n')
    f.write('    """Smoothly in-place cross-dissolve between two emotional facial expressions."""\n')
    f.write('    from_name = _normalize_behaviour(from_behaviour)\n')
    f.write('    to_name = _normalize_behaviour(to_behaviour)\n\n')
    f.write('    if not sys.stdout.isatty():\n')
    f.write('        show_portrait(to_name)\n')
    f.write('        return\n\n')
    f.write('    if ACTIVE_STYLE == "ascii":\n')
    f.write('        show_portrait(to_name)\n')
    f.write('        return\n\n')
    f.write('    grid_a = PORTRAIT_GRIDS.get(from_name) or PORTRAIT_GRIDS.get("cooperative")\n')
    f.write('    grid_b = PORTRAIT_GRIDS.get(to_name) or PORTRAIT_GRIDS.get("cooperative")\n\n')
    f.write('    if not grid_a or not grid_b or from_name == to_name:\n')
    f.write('        show_portrait(to_name)\n')
    f.write('        return\n\n')
    f.write('    height = len(grid_a)\n')
    f.write('    width = len(grid_a[0])\n\n')
    f.write('    sys.stdout.write(f"\\n{render_halfblock_grid(grid_a)}\\n")\n')
    f.write('    sys.stdout.flush()\n')
    f.write('    await asyncio.sleep(0.03)\n\n')
    f.write('    for f in range(1, frames + 1):\n')
    f.write('        t = f / frames\n')
    f.write('        t_eased = (1.0 - math.cos(t * math.pi)) / 2.0\n\n')
    f.write('        sys.stdout.write(f"\\033[{height}A\\r")\n')
    f.write('        sys.stdout.flush()\n\n')
    f.write('        frame = []\n')
    f.write('        for y in range(height):\n')
    f.write('            row = []\n')
    f.write('            row_a = grid_a[y]\n')
    f.write('            row_b = grid_b[y]\n')
    f.write('            for x in range(width):\n')
    f.write('                rta, gta, bta, rba, gba, bba = row_a[x]\n')
    f.write('                rtb, gtb, btb, rbb, gbb, bbb = row_b[x]\n')
    f.write('                rt = int((1.0 - t_eased) * rta + t_eased * rtb)\n')
    f.write('                gt = int((1.0 - t_eased) * gta + t_eased * gtb)\n')
    f.write('                bt = int((1.0 - t_eased) * bta + t_eased * btb)\n')
    f.write('                rb = int((1.0 - t_eased) * rba + t_eased * rbb)\n')
    f.write('                gb = int((1.0 - t_eased) * gba + t_eased * gbb)\n')
    f.write('                bb = int((1.0 - t_eased) * bba + t_eased * bbb)\n')
    f.write('                row.append((rt, gt, bt, rb, gb, bb))\n')
    f.write('            frame.append(row)\n\n')
    f.write('        sys.stdout.write(render_halfblock_grid(frame) + "\\n")\n')
    f.write('        sys.stdout.flush()\n')
    f.write('        await asyncio.sleep(delay)\n')

print(f"Successfully generated {output_path}!")
