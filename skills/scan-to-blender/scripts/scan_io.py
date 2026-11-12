# scan_io.py — find the project's RoomPlan scan and work out its import scale.
# Shared by inspect_scan.py, plan_view.py, room_survey.py and catalogue.py.
#   scan_path(root): $SCAN if set, else the only .usdz in <root>/source/scan/
#   scale_k():       multiplier from Blender units to metres for the imported scan.
#                    RoomPlan USDZ has imported at 1/10 scale before (a 7.8 m house came in as 0.78),
#                    so anything whose largest plan extent is under 4 units is assumed to be 1/10.
#                    Override with $SCAN_K. ALWAYS sanity-check the printed footprint against reality.
import bpy, glob, os
from mathutils import Vector

def scan_path(root):
    if os.environ.get("SCAN"):
        return os.environ["SCAN"]
    found = sorted(glob.glob(os.path.join(root, "source", "scan", "*.usdz")))
    if len(found) != 1:
        raise SystemExit(f"expected exactly one .usdz in source/scan (or set SCAN=...), found {found}")
    return found[0]

def scale_k():
    if os.environ.get("SCAN_K"):
        return float(os.environ["SCAN_K"])
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
    k = 10.0 if max(hi.x - lo.x, hi.y - lo.y) < 4.0 else 1.0
    print(f"scan_io: raw extent {hi.x - lo.x:.2f} x {hi.y - lo.y:.2f} units -> K = {k} "
          f"({(hi.x - lo.x) * k:.2f} x {(hi.y - lo.y) * k:.2f} m). Check this against the real space.")
    return k
