# _neighbours.py - when one room renders on its own, build the other rooms of the level too, so doorways
# and windows between rooms show the real next room instead of the outdoor ground plane.
# Usage in a room module's __main__, after build_asis():
#   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _neighbours; _neighbours.build("<this room>")
import os, glob, importlib, bpy

HERE = os.path.dirname(os.path.abspath(__file__))

def build(me):
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        name = os.path.splitext(os.path.basename(p))[0]
        if name.startswith("_") or name == me:
            continue
        mod = importlib.import_module(name)
        if hasattr(mod, "build_asis"):
            mod.build_asis()
    grounds = [o for o in bpy.data.objects if o.name == "ground" or o.name.startswith("ground.")]
    for o in grounds[1:]:
        bpy.data.objects.remove(o)
