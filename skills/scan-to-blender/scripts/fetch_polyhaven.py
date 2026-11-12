# fetch_polyhaven.py — download the Poly Haven (CC0) textures and HDRIs the room models use.
# Saves to assets/polyhaven/<id>/; already-downloaded files are skipped.
# Run: python scripts/fetch_polyhaven.py                       (the default lists below)
#      blender -b --python scripts/fetch_polyhaven.py -- tex:<id> ... hdri:<id> ... model:<id> ...
#      (no system Python needed: Blender's Python has urllib)
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "assets", "polyhaven")
RES = "2k"
UA = {"User-Agent": "floorplan-remodel/1.0 (personal project)"}

TEXTURES = [
    "herringbone_parquet", "wood_floor", "terrazzo_tiles",
    "white_oak_veneer", "american_walnut_veneer", "black_walnut_veneer_01",
    "marble_01", "white_plaster_02", "long_white_tiles",
    "wool_boucle", "brown_leather", "whitewashed_brick",
]
HDRIS = ["cloudy_vondelpark"]
MODELS = ["potted_plant_04", "potted_plant_02"]     # shelf plants: haworthia, syngonium
MODEL_RES = "1k"                                    # small on screen; 1k textures are plenty
MAPS = {"Diffuse": "diff", "Rough": "rough", "nor_gl": "nor"}   # Poly Haven map -> our file suffix
_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
if _args and not _args[0].endswith(".py"):
    TEXTURES = [a[4:] for a in _args if a.startswith("tex:")]
    HDRIS = [a[5:] for a in _args if a.startswith("hdri:")]
    MODELS = [a[6:] for a in _args if a.startswith("model:")]

def get(url, path):
    if os.path.exists(path):
        return
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(path, "wb") as f:
        f.write(r.read())
    print("  ", os.path.relpath(path, ROOT), f"{os.path.getsize(path) // 1024} KB")

def files(asset):
    with urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{asset}", headers=UA)) as r:
        return json.load(r)

for t in TEXTURES:
    d = os.path.join(DEST, t); os.makedirs(d, exist_ok=True)
    fl = files(t)
    print(t)
    for key, suffix in MAPS.items():
        if key in fl:
            get(fl[key][RES]["jpg"]["url"], os.path.join(d, f"{suffix}.jpg"))
for h in HDRIS:
    d = os.path.join(DEST, h); os.makedirs(d, exist_ok=True)
    print(h)
    get(files(h)["hdri"][RES]["hdr"]["url"], os.path.join(d, "sky.hdr"))
for m in MODELS:
    d = os.path.join(DEST, m); os.makedirs(d, exist_ok=True)
    print(m)
    blend = files(m)["blend"][MODEL_RES]["blend"]
    get(blend["url"], os.path.join(d, "model.blend"))
    for rel, inc in blend.get("include", {}).items():      # textures the .blend references
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        get(inc["url"], p)
