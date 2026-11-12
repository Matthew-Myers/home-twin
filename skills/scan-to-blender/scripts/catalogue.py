# catalogue.py — list every scanned object group with its model id, size and plan position.
# Run: blender -b -P scripts/catalogue.py
import bpy, os
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import scan_io
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=scan_io.scan_path(ROOT))
K = scan_io.scale_k()
objs = list(bpy.context.scene.objects)
meshes = [o for o in objs if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(map(min, *pts))

def top_group(o):
    while o.parent and not o.parent.name.startswith("node_"):
        o = o.parent
    return o

groups = {}
for o in meshes:
    g = top_group(o)
    groups.setdefault(g.name, []).append(o)

wall = meshes[0]
print("CAT world scale of an InnerSide:", [tuple(round(v, 4) for v in o.matrix_world.to_scale()) for o in meshes if o.name.startswith("InnerSide")][:2])
for name, parts in sorted(groups.items()):
    if not name.startswith(("furniture", "appliances", "plumbing", "structure", "door", "window")):
        continue
    c = [o.matrix_world @ Vector(v) for o in parts for v in o.bound_box]
    mn = Vector(map(min, *c)); mx = Vector(map(max, *c))
    sz = (mx - mn) * K; ctr = ((mn + mx) / 2 - lo) * K
    kind, model = name.split("_")[0], name.split("_")[1]
    print(f"CAT {kind:10} {model} size=({sz.x:.2f},{sz.y:.2f},{sz.z:.2f}) at=({ctr.x:.2f},{ctr.y:.2f}) parts={len(parts)} rot={tuple(round(v,2) for v in parts[0].matrix_world.to_euler())}")
