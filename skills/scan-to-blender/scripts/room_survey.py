# room_survey.py — dump every scanned element inside a plan box, in metres, for detailed room models.
# Run: blender -b -P scripts/room_survey.py -- x0 y0 x1 y1
import bpy, os, sys, math
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import scan_io
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
x0, y0, x1, y1 = map(float, sys.argv[sys.argv.index("--") + 1:][:4])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=scan_io.scan_path(ROOT))
K = scan_io.scale_k()
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(map(min, *pts))

def group_of(o):
    while o.parent and not o.parent.name.startswith("node_"):
        o = o.parent
    return o

groups = {}
for o in meshes:
    groups.setdefault(group_of(o).name, []).append(o)

rows = []
for name, parts in groups.items():
    vs = [(o.matrix_world @ v.co - lo) * K for o in parts for v in o.data.vertices]
    mn = Vector(map(min, *vs)); mx = Vector(map(max, *vs))
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    if not (x0 - 0.15 <= cx <= x1 + 0.15 and y0 - 0.15 <= cy <= y1 + 0.15):
        continue
    if name.startswith(("ExternalWalls", "FloorFiller")):
        continue
    kind = name.split("_")[0]
    extra = ""
    if kind == "InnerSide":
        n = (parts[0].matrix_world.to_3x3() @ parts[0].data.polygons[0].normal).normalized()
        extra = f" faces=({n.x:+.2f},{n.y:+.2f})"
    rot = math.degrees(group_of(parts[0]).matrix_world.to_euler().z)
    rows.append((kind, name.split("_")[1] if "_" in name else "", mn, mx, rot, extra))

for kind, model, mn, mx, rot, extra in sorted(rows, key=lambda r: (r[0], r[2].x, r[2].y)):
    print(f"SURVEY {kind:18} {model:9} x {mn.x:5.2f}-{mx.x:5.2f}  y {mn.y:5.2f}-{mx.y:5.2f}  z {mn.z:4.2f}-{mx.z:4.2f}  rot {rot:6.1f}{extra}")
