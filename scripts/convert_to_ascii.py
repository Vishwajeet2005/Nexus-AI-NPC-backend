import sys
import os
from PIL import Image, ImageEnhance

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Normalized face bounding boxes per emotion (1024x1024 coordinates)
CROPS = {
    "cooperative": (370, 190, 630, 510),  # 260x320
    "deflecting":  (270, 70,  830, 730),  # 560x660
    "nervous":     (330, 100, 670, 520),  # 340x420
    "hostile":     (240, 80,  820, 760),  # 580x680
    "confessing":  (210, 130, 730, 690),  # 520x560
}

ASCII_CHARS = " .:-=+*#%@"


def crop_and_enhance_face(img: Image.Image, emotion: str) -> Image.Image:
    """Extract tight facial expression bounding box and enhance facial contours."""
    box = CROPS.get(emotion, (250, 150, 750, 700))
    cropped = img.crop(box)
    
    # Lighting and facial detail enhancement:
    # 1. Lift shadows so eyes, pupils, lips and expression are clearly visible
    brightener = ImageEnhance.Brightness(cropped)
    enhanced = brightener.enhance(1.18)
    # 2. Boost contrast so facial contours, wrinkles and sweat stand out
    contrast = ImageEnhance.Contrast(enhanced)
    enhanced = contrast.enhance(1.22)
    # 3. Enhance sharpness for crisp edges
    sharpener = ImageEnhance.Sharpness(enhanced)
    enhanced = sharpener.enhance(1.4)
    return enhanced


def convert_face_to_halfblocks(image_path: str, emotion: str = "cooperative", width: int = 38, height_px: int = 38) -> list:
    """Convert portrait image to a 2D grid of TrueColor half-blocks (rt, gt, bt, rb, gb, bb)."""
    img = Image.open(image_path)
    face = crop_and_enhance_face(img, emotion)
    resized = face.resize((width, height_px), Image.Resampling.LANCZOS).convert("RGB")
    
    terminal_rows = height_px // 2
    grid = []
    for row in range(terminal_rows):
        y_top = row * 2
        y_bot = y_top + 1
        row_cells = []
        for x in range(width):
            rt, gt, bt = resized.getpixel((x, y_top))
            rb, gb, bb = resized.getpixel((x, y_bot))
            row_cells.append((rt, gt, bt, rb, gb, bb))
        grid.append(row_cells)
    return grid


def convert_face_to_ascii(image_path: str, emotion: str = "cooperative", width: int = 36, height: int = 18) -> str:
    """Convert portrait image to high-contrast compact ASCII characters."""
    img = Image.open(image_path)
    face = crop_and_enhance_face(img, emotion)
    resized = face.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")
    
    lines = []
    ramp_len = len(ASCII_CHARS)
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b = resized.getpixel((x, y))
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            idx = int((lum / 255.0) * (ramp_len - 1))
            char = ASCII_CHARS[idx]
            row.append(f"\033[38;2;{r};{g};{b}m{char}")
        lines.append("".join(row) + "\033[0m")
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "api/data/portraits/marcus_nervous.jpg"
    emo = sys.argv[2] if len(sys.argv) > 2 else "nervous"
    print(convert_face_to_ascii(path, emo))
