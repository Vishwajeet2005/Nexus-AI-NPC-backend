import os
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

with open(output_path, "w", encoding="utf-8") as f:
    f.write('"""Pre-computed photorealistic ANSI TrueColor ASCII portraits for Marcus Webb."""\n\n')
    f.write("PORTRAITS = {\n")
    for emotion, art in ascii_dict.items():
        f.write(f"    {emotion!r}: {art!r},\n")
    f.write("}\n")

print(f"Saved pre-computed portraits to {output_path}")
