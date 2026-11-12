# _neighbours.py - when one room renders on its own, build the other rooms of the level too, so doorways
# and windows between rooms show the real next room instead of the outdoor ground plane.
# Usage in a room module's __main__, after build_asis():
#   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _neighbours; _neighbours.build("<this room>")
# A neighbour that fails to import or build (another agent's half-written module) is skipped with a
# note, never fatal: this room's render doesn't depend on it.
import os, glob, importlib, bpy

HERE = os.path.dirname(os.path.abspath(__file__))

def build(me):
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        name = os.path.splitext(os.path.basename(p))[0]
        if name.startswith("_") or name == me:
            continue
        before = set(bpy.data.objects)
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "build_asis"):
                mod.build_asis()
        except Exception as e:
            for o in set(bpy.data.objects) - before:          # drop whatever it half-built
                bpy.data.objects.remove(o, do_unlink=True)
            print(f"_neighbours: {name} skipped ({type(e).__name__}: {e})")
    grounds = [o for o in bpy.data.objects if o.name == "ground" or o.name.startswith("ground.")]
    for o in grounds[1:]:
        bpy.data.objects.remove(o)
