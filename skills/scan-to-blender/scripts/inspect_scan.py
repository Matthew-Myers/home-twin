# inspect_scan.py — import the USDZ room scan, report its contents, render overview PNGs.
# Run: blender -b -P scripts/inspect_scan.py
import bpy, os, math
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import scan_io
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = scan_io.scan_path(ROOT)
OUT = os.path.join(ROOT, "renders")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=SCAN)

lo = Vector((1e9, 1e9, 1e9)); hi = -lo
print("=== OBJECTS ===")
for ob in bpy.context.scene.objects:
    line = f"{ob.type:8} {ob.name}"
    if ob.type == 'MESH':
        corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        mn = Vector(map(min, *corners)); mx = Vector(map(max, *corners))
        lo = Vector(map(min, lo, mn)); hi = Vector(map(max, hi, mx))
        line += f"  verts={len(ob.data.vertices)} size={tuple(round(v,2) for v in (mx-mn))} min={tuple(round(v,2) for v in mn)}"
    print(line)
print("=== BOUNDS ===", tuple(round(v,2) for v in lo), tuple(round(v,2) for v in hi))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
world = bpy.data.worlds.new("w"); scene.world = world
world.color = (1, 1, 1)

ctr = (lo + hi) / 2; span = max(hi.x - lo.x, hi.y - lo.y)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
sun.data.energy = 3; sun.rotation_euler = (math.radians(30), 0, math.radians(40))
scene.collection.objects.link(sun)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = 'ORTHO'

def shot(name, loc, rot, scale):
    cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = scale
    cam.data.clip_end = 1000
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)

# top-down, cut at ~1.5 m by placing camera inside? Use clip_start to slice off ceiling.
cam.data.clip_start = 0.1
shot("scan_top.png", (ctr.x, ctr.y, hi.z + 1), (0, 0, 0), span * 1.1)
shot("scan_iso.png", (ctr.x + span, ctr.y - span, hi.z + span), (math.radians(55), 0, math.radians(45)), span * 1.3)
