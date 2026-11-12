# example_level.py - Phase 2 floorplan for a small made-up two-room cottage (living room + kitchen).
# In a real project this is scripts/level.py and every number comes from room_survey.py and the
# stills; here the numbers are invented. Shows: clean walls with rk.shell (built outward from the
# interior faces), openings, windows, scanned items as labelled blocks, plan + cutaway renders.
# Run: blender -b -P scripts/level.py      -> renders/level_plan.jpg, renders/level_cutaway.jpg
# Coordinates: plan metres from the level's SW corner, x east, y north, z = 0 at the floor.
import bpy, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, roomkit as rk
importlib.reload(rk)
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CEILING = 2.44          # scan wall height (8'0")
CUT = 1.5               # cutaway / plan wall height

# ---------------------------------------------------------------- rooms (interior faces, CCW)
# Openings per edge: (start, end, bottom, top), measured along the edge from its first corner.
LIVING = [(0.0, 0.0), (5.2, 0.0), (5.2, 6.0), (0.0, 6.0)]
LIVING_OPEN = {0: [(0.3, 1.2, 0, 2.05),          # front door, south wall
                   (3.4, 4.8, 0.85, 2.05)],      # picture window, south wall
               1: [(3.4, 4.6, 0, 2.10)],          # cased opening east to the kitchen, y 3.4-4.6
               3: [(2.0, 3.6, 0.85, 2.05)]}       # window, west wall y 4.0-2.4
KITCHEN = [(5.32, 0.0), (8.6, 0.0), (8.6, 6.0), (5.32, 6.0)]   # 0.12 m wall between the rooms
KITCHEN_OPEN = {1: [(3.6, 4.5, 0, 2.05)],         # back door, east wall y 3.6-4.5
                2: [(1.2, 2.4, 1.05, 2.05)],      # window over the sink, north wall x 7.4-6.2
                3: [(1.4, 2.6, 0, 2.10)]}         # the cased opening from the living room

# scanned furniture (from the survey), as blocks: (label, x0, y0, x1, y1, h, kind)
SCAN_ITEMS = [
    ("sofa", 1.15, 5.05, 3.35, 5.97, 0.85, "furniture"),
    ("tv console", 1.5, 0.0, 3.0, 0.42, 0.64, "furniture"),
    ("bookcase", 4.05, 5.62, 4.95, 5.97, 1.90, "furniture"),
    ("table", 6.5, 2.5, 7.5, 3.5, 0.75, "furniture"),
    ("fridge", 7.65, 5.25, 8.55, 6.0, 1.78, "appliance"),
    ("range", 6.22, 0.0, 6.98, 0.66, 0.92, "appliance"),
]
# built-ins the scan has no category for, added from the stills (lesson 3): kitchen runs
KITCHEN_RUNS = [((8.6, 6.0), (5.32, 6.0), 0.95, 3.28),    # north run, u from the NE corner going west
                ((5.32, 0.0), (8.6, 0.0), 0.3, 2.4)]      # south run, u from the SW corner going east

def named(prefix, fn, *a, **kw):
    """run a builder and prefix every new object with the room name (no 'floor.001' clashes)"""
    before = set(bpy.data.objects)
    out = fn(*a, **kw)
    for o in set(bpy.data.objects) - before:
        o.name = f"{prefix}_{o.name}"
    return out

def build():
    rk.reset()
    wall = rk.mat("wall", (0.86, 0.85, 0.81), 0.9)
    oak = rk.mat("oak_floor", (0.55, 0.40, 0.26), 0.5)
    tile = rk.mat("tile_floor", (0.70, 0.70, 0.68), 0.4)
    trim = rk.mat("trim", (0.93, 0.93, 0.91), 0.5)
    named("living", rk.shell, LIVING, CEILING, LIVING_OPEN, wall, oak)
    named("kitchen", rk.shell, KITCHEN, CEILING, KITCHEN_OPEN, wall, tile)
    for o in [o for o in bpy.data.objects if o.name.endswith("ground") or "ground." in o.name][1:]:
        bpy.data.objects.remove(o)                  # one outdoor ground plane is enough
    named("living", rk.window, rk.Frame(LIVING[0], LIVING[1]), 3.4, 4.8, 0.85, 2.05, trim, (2, 1))
    named("living", rk.window, rk.Frame(LIVING[3], LIVING[0]), 2.0, 3.6, 0.85, 2.05, trim, (2, 1))
    named("kitchen", rk.window, rk.Frame(KITCHEN[2], KITCHEN[3]), 1.2, 2.4, 1.05, 2.05, trim, (2, 1))
    rk.box("living_threshold", 5.2, 3.4, -0.01, 5.32, 4.6, 0.0, oak, 0)   # floor through the wall opening
    kind_m = {"appliance": rk.mat("appliance", (0.85, 0.85, 0.86), 0.3),
              "furniture": rk.mat("furniture", (0.45, 0.62, 0.45), 0.7)}
    cab = rk.mat("cabinet_block", (0.55, 0.60, 0.70), 0.7)
    for p0, p1, u0, u1 in KITCHEN_RUNS:
        rk.Frame(p0, p1).box("item_counter", u0, u1, 0, 0.62, 0, 0.92, cab)
    for label, x0, y0, x1, y1, h, kind in SCAN_ITEMS:
        rk.box("item_" + label, x0, y0, 0, x1, y1, h, kind_m[kind])

KEEP_IN_CUTAWAY = ()     # name prefixes of structure that must show above the cut (beams, posts)

def cut_walls(top):
    """cutaway: drop ceilings, squash everything above `top` (except KEEP_IN_CUTAWAY)"""
    for o in list(bpy.data.objects):
        if o.type != 'MESH' or (KEEP_IN_CUTAWAY and o.name.startswith(KEEP_IN_CUTAWAY)):
            continue
        if "ceiling" in o.name:
            o.hide_render = True
            continue
        mw = o.matrix_world
        zs = [(mw @ v.co).z for v in o.data.vertices]
        if zs and min(zs) >= top:
            o.hide_render = True
            continue
        inv = mw.inverted()
        for v in o.data.vertices:
            w = mw @ v.co
            if w.z > top:
                w.z = top; v.co = inv @ w

def lights():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new("w")
    s.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.57, 0.6, 1)
    s.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    sun = rk.link(bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(8), math.radians(4), 0)     # near-overhead: short shadows
    return sun

def ft_in(m):
    i = round(m / 0.0254)
    return f"{i // 12}'{i % 12}\""

# (name, label x, label y, (room width, room depth) or None)
LABELS = [("LIVING", 2.6, 2.6, (5.2, 6.0)),
          ("KITCHEN", 6.96, 4.3, (3.28, 6.0))]

def labels():
    ink = rk.emissive("ink", (0.55, 0.02, 0.02), 0.3)
    for name, x, y, size in LABELS:
        body = name if not size else f"{name}\n{size[0]:.2f} x {size[1]:.2f} m\n{ft_in(size[0])} x {ft_in(size[1])}"
        cu = bpy.data.curves.new(name, 'FONT'); cu.body = body
        cu.size = 0.28 if size else 0.22; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        t = rk.link(bpy.data.objects.new("label_" + name, cu)); t.location = (x, y, CUT + 0.6)
        t.visible_shadow = False
        cu.materials.append(ink)

if __name__ == "__main__":
    build()
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "level.blend"))
    cut_walls(CUT)
    sun = lights()
    labels()
    ctr = Vector((4.3, 3.0, 0))
    # plan: orthographic, straight down, north up
    cam = rk.camera("plan", ctr + Vector((0, 0, 20)), ctr, 50)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 9.6
    rk.render(cam, os.path.join(ROOT, "renders", "level_plan.jpg"), (1600, 1200))
    # cutaway: 3/4 view from the south-east at 55 deg elevation
    for o in bpy.data.objects:
        if o.name.startswith("label_"):
            o.hide_render = True
    sun.rotation_euler = (math.radians(35), math.radians(15), math.radians(20))
    el, az, d = math.radians(55), math.radians(25), 40
    eye = ctr + Vector((d * math.cos(el) * math.sin(az), -d * math.cos(el) * math.cos(az), d * math.sin(el)))
    cam2 = rk.camera("cutaway", eye, ctr, 50)
    cam2.data.type = 'ORTHO'; cam2.data.ortho_scale = 10.5
    rk.render(cam2, os.path.join(ROOT, "renders", "level_cutaway.jpg"), (1600, 1200))
