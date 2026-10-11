import sys
import os
from PIL import Image, ImageEnhance

# Character gradient from dense to sparse (dark to light or vice versa)
# Using standard high-density ASCII ramp
ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

def convert_face_to_ascii(image_path, width=54, crop_face=True):
    img = Image.open(image_path)
    
    if crop_face:
        # Tight crop on Marcus's face from the 1024x1024 generated portrait
        w, h = img.size
        left = int(w * 0.22)
        top = int(h * 0.16)
        right = int(w * 0.78)
        bottom = int(h * 0.76)
        img = img.crop((left, top, right, bottom))
    
    # Boost contrast and sharpness for crisp ASCII edges
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.25)
    sharpener = ImageEnhance.Sharpness(img)
    img = sharpener.enhance(1.4)

    # In terminal fonts, characters are ~2x taller than wide
    char_aspect = 0.48
    aspect_ratio = img.height / img.width
    height = int(width * aspect_ratio * char_aspect)
    
    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    img_rgb = img_resized.convert("RGB")
    
    lines = []
    ramp_len = len(ASCII_CHARS)
    
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b = img_rgb.getpixel((x, y))
            # Standard perceptual luminance formula
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            # Map luminance: brighter areas get lighter characters, dark get dense
            idx = int((1.0 - (lum / 255.0)) * (ramp_len - 1))
            char = ASCII_CHARS[idx]
            # TrueColor 24-bit ANSI
            row.append(f"\033[38;2;{r};{g};{b}m{char}")
        lines.append("".join(row) + "\033[0m")
    
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        w = int(sys.argv[2]) if len(sys.argv) > 2 else 54
        print(convert_face_to_ascii(path, w))
