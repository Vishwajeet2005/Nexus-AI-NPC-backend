import sys
import os
from PIL import Image, ImageEnhance

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Normalized facial expression crops per emotion (1024x1024 coordinates)
CROPS = {
    "cooperative": (340, 180, 660, 520),  # 320x340
    "deflecting":  (250, 70,  810, 730),  # 560x660
    "nervous":     (310, 90,  690, 530),  # 380x440
    "hostile":     (220, 80,  820, 760),  # 600x680
    "confessing":  (200, 120, 740, 700),  # 540x580
}

# Rich typography ASCII ramp from dense/opaque to sparse/empty
ASCII_CHARS = "@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "


def crop_and_enhance_face(img: Image.Image, emotion: str) -> Image.Image:
    """Extract tight facial expression bounding box and enhance facial contours."""
    box = CROPS.get(emotion, (250, 150, 750, 700))
    face = img.crop(box)
    
    # Lighting and facial detail enhancement:
    # 1. Lift shadows so eyes, pupils, lips and expression are clearly visible
    brightener = ImageEnhance.Brightness(face)
    enhanced = brightener.enhance(1.18)
    # 2. Boost contrast so facial contours, wrinkles and sweat stand out
    contrast = ImageEnhance.Contrast(enhanced)
    enhanced = contrast.enhance(1.25)
    # 3. Enhance sharpness for crisp typography edges
    sharpener = ImageEnhance.Sharpness(enhanced)
    enhanced = sharpener.enhance(1.4)
    return enhanced


def convert_face_to_ascii_grid(image_path: str, emotion: str = "cooperative", width: int = 46) -> list:
    """Convert portrait image to a 2D grid of (r, g, b, char) tuples."""
    img = Image.open(image_path)
    face = crop_and_enhance_face(img, emotion)
    
    char_aspect = 0.48
    aspect = face.height / face.width
    height = int(width * aspect * char_aspect)
    
    resized = face.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")
    ramp_len = len(ASCII_CHARS)
    grid = []
    
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b = resized.getpixel((x, y))
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            norm_lum = lum / 255.0
            idx = int((1.0 - norm_lum) * (ramp_len - 1))
            idx = max(0, min(ramp_len - 1, idx))
            char = ASCII_CHARS[idx]
            if lum < 15:
                char = " "
            row.append((r, g, b, char))
        grid.append(row)
    return grid


def render_ascii_grid(grid: list) -> str:
    """Format a 2D grid of (r, g, b, char) tuples into ANSI TrueColor escape strings."""
    lines = []
    for row in grid:
        row_chars = []
        for r, g, b, c in row:
            if c == " ":
                row_chars.append(" ")
            else:
                row_chars.append(f"\033[38;2;{r};{g};{b}m{c}")
        lines.append("".join(row_chars) + "\033[0m")
    return "\n".join(lines)


def convert_face_to_ascii(image_path: str, emotion: str = "cooperative", width: int = 46) -> str:
    """Convert portrait image to fine-grained TrueColor ASCII text."""
    grid = convert_face_to_ascii_grid(image_path, emotion, width)
    return render_ascii_grid(grid)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "api/data/portraits/marcus_nervous.jpg"
    emo = sys.argv[2] if len(sys.argv) > 2 else "nervous"
    print(convert_face_to_ascii(path, emo))
