# plan_view.py — top-down plan of the scan with a 1 m grid, to identify rooms.
# Run: blender -b -P scripts/plan_view.py
import bpy, os, math
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import scan_io
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = scan_io.scan_path(ROOT)
OUT = os.path.join(ROOT, "renders", "scan_plan.png")
PX_PER_M = 70

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=SCAN)
scene = bpy.context.scene

meshes = [o for o in scene.objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
print("unit size:", tuple(round(v, 3) for v in hi - lo), "scene unit scale:", scene.unit_settings.scale_length)

# RoomPlan scans may import at 1/10 scale (scan_io works out K): report and draw in metres
K = scan_io.scale_k()
w_m, h_m = (hi.x - lo.x) * K, (hi.y - lo.y) * K
print(f"house footprint: {w_m:.2f} x {h_m:.2f} m, wall height {(hi.z - lo.z) * K:.2f} m")

# 1 m grid lines just above the floor
grid = bpy.data.materials.new("grid"); grid.diffuse_color = (1, 0, 0, 1)
for i in range(int(w_m) + 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(lo.x + i / K, (lo.y + hi.y) / 2, hi.z + 0.015))
    o = bpy.context.object; o.scale = (0.002, hi.y - lo.y, 0.001); o.data.materials.append(grid)
for j in range(int(h_m) + 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((lo.x + hi.x) / 2, lo.y + j / K, hi.z + 0.015))
    o = bpy.context.object; o.scale = (hi.x - lo.x, 0.002, 0.001); o.data.materials.append(grid)

# colour by RoomPlan category; drop the ceiling slab
def mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        bsdf.inputs["Roughness"].default_value = 1.0
    return m
COLOURS = [("FloorFillerTop", None), ("ExternalWalls", None),("InnerSide", (0.1, 0.1, 0.1)),
           ("door", (0.9, 0.5, 0.1)), ("window", (0.2, 0.6, 1.0)), ("frame", (0.2, 0.6, 1.0)),
           ("furniture", (0.55, 0.8, 0.55)), ("appliances", (0.8, 0.55, 0.8)),
           ("plumbing", (0.4, 0.8, 0.9)), ("structure", (0.95, 0.85, 0.3)), ("WholeFloor", (0.93, 0.93, 0.93))]
for o in meshes:
    for key, rgb in COLOURS:
        if key.lower() in o.name.lower() or (o.parent and key.lower() in o.parent.name.lower()):
            if rgb is None:
                o.hide_render = True
            else:
                o.data.materials.clear(); o.data.materials.append(mat(key, rgb))
            break

# RoomPlan walls are zero-thickness panels hidden under the floor surface from above:
# draw each one as a flat dark bar on top of the model instead
WALL_T_M = 0.12
dark = mat("wallbar", (0.08, 0.08, 0.08))
for o in meshes:
    if o.name.startswith("InnerSide"):
        c = [o.matrix_world @ Vector(v) for v in o.bound_box]
        x0, x1 = min(v.x for v in c), max(v.x for v in c)
        y0, y1 = min(v.y for v in c), max(v.y for v in c)
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, hi.z + 0.01))
        b = bpy.context.object
        b.scale = (max(x1 - x0, WALL_T_M / K), max(y1 - y0, WALL_T_M / K), 0.001)
        b.data.materials.append(dark)

# Room-name guesses, in metres from the plan's bottom-left corner. Pass them as
#   blender -b -P plan_view.py -- "OFFICE?:6.1:15.4" "HALL:4.4:13.0" ...   ("\n" in a name = line break)
# First run with no labels, look at the grid, then re-run with your guesses for the user to confirm.
import sys
_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LABELS = [(a.rsplit(":", 2)[0].replace("\\n", "\n"), float(a.rsplit(":", 2)[1]), float(a.rsplit(":", 2)[2]))
          for a in _args]
ink = mat("ink", (0.8, 0.0, 0.0))
for txt, x, y in LABELS:
    cu = bpy.data.curves.new(txt, 'FONT'); cu.body = txt
    cu.size = 0.45 / K; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    t = bpy.data.objects.new(txt, cu); scene.collection.objects.link(t)
    t.location = (lo.x + x / K, lo.y + y / K, hi.z + 0.02)
    cu.materials.append(ink)

scene.render.engine = 'BLENDER_EEVEE'
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.6, 0.6, 0.6)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
sun.data.energy = 3; scene.collection.objects.link(sun)   # straight down: no long shadows
scene.render.resolution_x = int(w_m * PX_PER_M * 1.08)
scene.render.resolution_y = int(h_m * PX_PER_M * 1.08)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = max(hi.x - lo.x, hi.y - lo.y) * 1.08
cam.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z + 1)
CUT_M = 3.0                      # plan cut height above the floor, metres
cam.data.clip_start = cam.location.z - (lo.z + CUT_M / K)
cam.data.clip_end = 10
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
