# kitchen_nook.py - concept "nook" for the demo cottage's kitchen: an UPDATE (fronts, fixtures,
# furniture; no walls or plumbing move).
# Shows: removing by name + box (names repeat along every wall), building on the room's own wall
# frames (room.F_S), adding a ceiling fixture with the "ceiling_" prefix, and a clearance check
# printed for the write-up.
# Run: blender -b -P scripts/concepts/kitchen_nook.py -- [test|final] [before] [cam ...]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import roomkit as rk, conceptkit as ck

INFO = dict(
    title="Open nook",
    scope="update",
    idea="Navy cabinets, open oak shelves on the range wall, a long table under a linear light.",
    changes=["cabinets painted navy", "range-wall uppers -> two open oak shelves each side",
             "round table + 4 chairs -> 1.5 x 0.85 m table + 4 chairs",
             "dome pendant -> linear flush light over the table"],
    keeps=["layout, counters, appliances, hood", "sink-wall uppers"],
)

SOUTH_WALL = (5.3, -0.1, 1.3, 8.7, 0.5, 2.5)      # x0 y0 z0 x1 y1 z1: the range wall's upper zone
DINING = (5.9, 1.9, 0.0, 8.1, 4.1, 1.3)           # the round table and its chairs
SOUTH_RUN = (5.3, -0.1, 0.0, 8.7, 0.8, 1.0)       # base cabinets + counters on the range wall

def change(room):
    oak = rk.mat("shelf_oak", (0.62, 0.45, 0.28), 0.5)
    ck.swap_material("cab_green", rk.mat("cab_navy", (0.09, 0.12, 0.20), 0.5))

    ck.remove("kitchen_upper*", "kitchen_udoor*", box=SOUTH_WALL)
    for u0, u1 in ((0.30, 0.85), (1.71, 2.40)):                    # either side of the hood
        ck.add("kitchen_", rk.open_shelves, room.F_S, u0, u1, (1.50, 1.88), oak)

    ck.remove("kitchen_*", box=DINING, keep=("kitchen_floor*", "kitchen_zone*", "kitchen_cut*"))  # floor's centre is in there too
    ck.remove("pendant", "ceiling_pendant_fitting*")
    ck.add("kitchen_", rk.rect_table, 6.25, 2.575, 7.75, 3.425, 0.75, oak, rk.mat("black_metal", (0.03, 0.03, 0.03), 0.4, 0.6))
    for x in (6.65, 7.35):
        ck.add("kitchen_", rk.chair, x, 2.15, 90, oak, style="windsor")
        ck.add("kitchen_", rk.chair, x, 3.85, 270, oak, style="windsor")
    # an open flush mount lights the whole ceiling where the shaded dome lit mostly the table:
    # keep the room's light level comparable, or the "after" just looks over-exposed
    ck.add("ceiling_", rk.alabaster_linear, 7.0, 3.0, room.CEILING, length=0.9, along="x", watts=18)

    gap = ck.clearance(ck.extent("kitchen_table*"), ck.extent("kitchen_counter*", box=SOUTH_RUN))
    print(f"kitchen_nook: table to range-wall counter {gap:.2f} m "
          f"({gap / 0.0254:.0f} in; walkway behind seated diners wants ~0.91 m / 36 in)")

ck.run("kitchen", "nook", change, INFO)
