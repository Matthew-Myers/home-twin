# house.py - assemble every as-is room module of this level into one scene and render whole-level views.
# Generic: builds scripts/rooms/<name>.py for every module that exposes build_asis() (or the list in
# ROOM_MODULES below). All modules share plan coordinates (metres from the level's SW corner), so they stack.
#
# Run: blender -b -P scripts/house.py               Cycles finals -> renders/house/final_<view>.jpg + house.blend
#      blender -b -P scripts/house.py -- preview    quick 64-sample pass -> renders/house/preview_<view>.jpg
#      blender -b -P scripts/house.py -- plan iso   only those views
import bpy, os, sys, math, importlib, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "rooms"))
import roomkit as rk

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "renders", "house")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "preview" in ARGS
ONLY = [a for a in ARGS if a != "preview"]

ROOM_MODULES = None          # None = every scripts/rooms/*.py with build_asis(); or a list of names in build order
EXPOSURE = -0.3
# name prefixes cut away in top views: ceilings and everything hung from them
# (roomkit's ceiling fixtures use these names; room modules prefix their own ceiling-hung things "ceiling_")
HIDE_FROM_ABOVE = ("ceiling", "pendant", "can_", "alabaster", "linear_alabaster")

def room_names():
    if ROOM_MODULES:
        return ROOM_MODULES
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(HERE, "rooms", "*.py"))
                  if not os.path.basename(p).startswith("_"))

def build_house(log=print):
    """build every room into the current scene; returns the rooms that built"""
    built = []
    for name in room_names():
        try:
            mod = importlib.import_module(name)
            importlib.reload(mod)
            if not hasattr(mod, "build_asis"):
                log(f"house: {name} has no build_asis(), skipping")
                continue
            mod.build_asis()
            built.append(name)
        except Exception as e:                      # a half-written module must not sink the whole level
            log(f"house: {name} failed to build, SKIPPED ({type(e).__name__}: {e})")
    grounds = [o for o in bpy.data.objects if o.name == "ground" or o.name.startswith("ground.")]
    for o in grounds[1:]:
        bpy.data.objects.remove(o)                 # one outdoor ground plane is enough
    return built

def level_bounds():
    xs, ys = [], []
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.name.startswith("ground"):
            for c in o.bound_box:
                w = o.matrix_world @ __import__("mathutils").Vector(c)
                xs.append(w.x); ys.append(w.y)
    return min(xs), min(ys), max(xs), max(ys)

def views(b):
    x0, y0, x1, y1 = b
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    long_y = h >= w
    span = max(w, h) * 1.06
    short = round(2200 * (min(w, h) * 1.06 + 0.3) / span)     # frame follows the footprint's aspect
    return {
        # true plan: orthographic, straight down, north up (ortho_scale spans the longer side)
        "plan": dict(eye=(cx, cy, 40), target=(cx, cy, 0), scale=span,
                     res=(short, 2200) if long_y else (2200, short)),
        # 3/4 view from the south-east, 50 deg down, long axis across the frame
        "iso": dict(eye=(cx + 30 * math.cos(math.radians(50)) * (0.85 if long_y else 0.3),
                         cy - 30 * math.cos(math.radians(50)) * (0.5 if long_y else 0.95),
                         30 * math.sin(math.radians(50))),
                    target=(cx, cy, 0.5), scale=span * 1.12, res=(2400, 1600)),   # 0.98 clipped corners
        # 3/4 view from the south-west
        "iso_sw": dict(eye=(cx - 30 * math.cos(math.radians(50)) * 0.85, cy - 30 * math.cos(math.radians(50)) * 0.5,
                            30 * math.sin(math.radians(50))),
                       target=(cx, cy, 0.5), scale=span * 1.12, res=(2400, 1600)),
    }

def view_camera(name, cfg):
    cam = rk.camera(name, cfg["eye"], cfg["target"], 50)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = cfg["scale"]
    cam.data.clip_end = 300
    return cam

if __name__ == "__main__":
    rk.reset()
    rk._mats.clear()
    rk.use_cycles(64 if PREVIEW else 192, EXPOSURE)
    # overcast sky for the outside + a soft near-overhead sun so the cut-open rooms read from above;
    # the rooms' own fixtures stay on
    rk.daylight(sun_dir=(18, 8, 30), sun_strength=1.6, sky=(0.62, 0.70, 0.80), sky_strength=0.8)
    built = build_house()
    print("house: built", built)
    for o in bpy.data.objects:
        if o.type != 'LIGHT' and o.name.startswith(HIDE_FROM_ABOVE):   # keep the light, hide the fitting
            o.hide_render = True
        if o.type == 'LIGHT':
            o.visible_glossy = False
    os.makedirs(OUT, exist_ok=True)
    for name, cfg in views(level_bounds()).items():
        if ONLY and name not in ONLY:
            continue
        rk.render(view_camera(name, cfg), os.path.join(OUT, f"{'preview' if PREVIEW else 'final'}_{name}.jpg"), cfg["res"])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house.blend"))
