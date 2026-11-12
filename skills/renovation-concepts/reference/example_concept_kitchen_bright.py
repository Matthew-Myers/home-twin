# kitchen_bright.py - concept "bright" for the demo cottage's kitchen: a REFRESH (finishes only).
# Shows: swap_material to repaint every cabinet / change hardware / relay the floor in one line each.
# Nothing moves, so it needs no clearance check.
# Run: blender -b -P scripts/concepts/kitchen_bright.py -- [test|final] [before] [cam ...]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import roomkit as rk, conceptkit as ck

INFO = dict(
    title="Bright",
    scope="refresh",
    idea="Same layout, lighter and warmer: off-white cabinets, black hardware, oak floor.",
    changes=["cabinets painted warm off-white", "brass pulls -> matte black",
             "tile floor -> light oak planks"],
    keeps=["layout, counters, appliances", "table, chairs, pendant"],
)

def change(room):
    ck.swap_material("cab_green", rk.mat("cab_offwhite", (0.88, 0.86, 0.80), 0.5))
    ck.swap_material("brass", rk.mat("pull_black", (0.02, 0.02, 0.02), 0.45, 0.8))
    ck.swap_material("kitchen_tile*", rk.plank_floor("oak_planks", (0.72, 0.55, 0.36), (0.55, 0.38, 0.22)))

ck.run("kitchen", "bright", change, INFO)
