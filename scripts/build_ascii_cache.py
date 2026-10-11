import os
import sys

sys.path.insert(0, os.path.abspath("."))
from scripts.convert_to_ascii import convert_face_to_ascii

PORTRAITS = {
    "cooperative": "api/data/portraits/marcus_cooperative.jpg",
    "deflecting":  "api/data/portraits/marcus_deflecting.jpg",
    "nervous":     "api/data/portraits/marcus_nervous.jpg",
    "hostile":     "api/data/portraits/marcus_hostile.jpg",
    "confessing":  "api/data/portraits/marcus_confess.jpg",
}

output_path = "api/data/portraits/ascii_cache.py"
ascii_dict = {}

for emotion, img_path in PORTRAITS.items():
    if os.path.exists(img_path):
        print(f"Converting {emotion} from {img_path}...")
        ascii_dict[emotion] = convert_face_to_ascii(img_path, width=50)
    else:
        print(f"Warning: {img_path} not found!")

HELPER_CODE = '''
import asyncio
import math
import os
import re
import sys

# 8x8 Bayer dithering matrix normalized to [0, 1)
BAYER_8X8 = [
    [ 0/64, 32/64,  8/64, 40/64,  2/64, 34/64, 10/64, 42/64],
    [48/64, 16/64, 56/64, 24/64, 50/64, 18/64, 58/64, 26/64],
    [12/64, 44/64,  4/64, 36/64, 14/64, 46/64,  6/64, 38/64],
    [60/64, 28/64, 52/64, 20/64, 62/64, 30/64, 54/64, 22/64],
    [ 3/64, 35/64, 11/64, 43/64,  1/64, 33/64,  9/64, 41/64],
    [51/64, 19/64, 59/64, 27/64, 49/64, 17/64, 57/64, 25/64],
    [15/64, 47/64,  7/64, 39/64, 13/64, 45/64,  5/64, 37/64],
    [63/64, 31/64, 55/64, 23/64, 61/64, 29/64, 53/64, 21/64],
]


def _normalize_behaviour(behaviour) -> str:
    name = str(getattr(behaviour, "value", behaviour)).lower()
    if name == "confess":
        return "confessing"
    return name


def _parse_grid(art_str: str):
    grid = []
    for line in art_str.split("\\n"):
        tokens = re.findall(r"\\x1b\\[38;2;(\\d+);(\\d+);(\\d+)m(.)", line)
        if tokens:
            grid.append([(int(r), int(g), int(b), c) for r, g, b, c in tokens])
    return grid


# Pre-parsed 2D pixel grids: dict[emotion, list[list[(r, g, b, char)]]]
PORTRAIT_GRIDS = {k: _parse_grid(v) for k, v in PORTRAITS.items()}


def render_grid(grid) -> str:
    """Format a 2D pixel grid into ANSI TrueColor escape sequence strings."""
    lines = []
    for row in grid:
        lines.append("".join(f"\\033[38;2;{r};{g};{b}m{c}" for r, g, b, c in row) + "\\033[0m")
    return "\\n".join(lines)


def show_portrait(behaviour: str):
    """Print the static portrait for Marcus Webb."""
    name = _normalize_behaviour(behaviour)
    art = PORTRAITS.get(name) or PORTRAITS.get("cooperative")
    if art:
        print(f"\\n{art}")


async def morph_portrait(from_behaviour: str, to_behaviour: str, frames: int = 10, delay: float = 0.035):
    """Smoothly in-place cross-fade / morph between two emotional expressions.

    Uses cosine easing, TrueColor 24-bit RGB interpolation, and 8x8 Bayer
    dithered spatial dissolution to achieve lifelike human facial emotion transitions.
    """
    from_name = _normalize_behaviour(from_behaviour)
    to_name = _normalize_behaviour(to_behaviour)

    # In non-interactive environments (CI, redirected stdout), render static portrait
    if not sys.stdout.isatty():
        show_portrait(to_name)
        return

    grid_a = PORTRAIT_GRIDS.get(from_name) or PORTRAIT_GRIDS.get("cooperative")
    grid_b = PORTRAIT_GRIDS.get(to_name) or PORTRAIT_GRIDS.get("cooperative")

    if not grid_a or not grid_b or from_name == to_name:
        show_portrait(to_name)
        return

    height = len(grid_a)
    width = len(grid_a[0])

    # 1. Display starting portrait frame
    sys.stdout.write(f"\\n{render_grid(grid_a)}\\n")
    sys.stdout.flush()
    await asyncio.sleep(0.04)

    # 2. Animate morph frames in-place using ANSI cursor repositioning
    for f in range(1, frames + 1):
        t = f / frames
        t_eased = (1.0 - math.cos(t * math.pi)) / 2.0

        # Move cursor up by portrait height and carriage-return to col 0
        sys.stdout.write(f"\\033[{height}A\\r")
        sys.stdout.flush()

        frame = []
        for y in range(height):
            row = []
            row_a = grid_a[y]
            row_b = grid_b[y]
            for x in range(width):
                ra, ga, ba, ca = row_a[x]
                rb, gb, bb, cb = row_b[x]

                r = int((1.0 - t_eased) * ra + t_eased * rb)
                g = int((1.0 - t_eased) * ga + t_eased * gb)
                b = int((1.0 - t_eased) * ba + t_eased * bb)

                threshold = BAYER_8X8[y % 8][x % 8]
                char = cb if t_eased >= threshold else ca
                row.append((r, g, b, char))
            frame.append(row)

        sys.stdout.write(render_grid(frame) + "\\n")
        sys.stdout.flush()
        await asyncio.sleep(delay)
'''

with open(output_path, "w", encoding="utf-8") as f:
    f.write('"""Pre-computed photorealistic ANSI TrueColor ASCII portraits for Marcus Webb."""\\n\\n')
    f.write("PORTRAITS = {\\n")
    for emotion, art in ascii_dict.items():
        f.write(f"    {emotion!r}: {art!r},\\n")
    f.write("}\\n\\n")
    f.write(HELPER_CODE)

print(f"Saved pre-computed portraits to {output_path}")
