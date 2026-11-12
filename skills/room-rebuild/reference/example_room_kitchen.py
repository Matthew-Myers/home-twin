# kitchen.py - kitchen of the made-up demo cottage, detail level "decluttered".
# Shows: cabinet runs on wall frames with roomkit's Style / base_unit / upper_unit / countertop,
# appliances, a dining table with chairs and a pendant, the same modes as example_room_living.py.
# Run: blender -b -P scripts/rooms/kitchen.py [-- final [test]] [cam ...]
import bpy, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import roomkit as rk, project as pj

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOM = "kitchen"
OUT = os.path.join(ROOT, "renders", ROOM)

# ---------------------------------------------------------------- geometry: from project.json
OUTLINE, OPENINGS, CEILING = pj.geometry(ROOM)
(BACK_DOOR,) = OPENINGS[1]              # edge 1 (east)
(WINDOW,) = OPENINGS[2]                 # edge 2 (north), over the sink
(TO_LIVING,) = OPENINGS[3]              # edge 3 (west)
F_S, F_E, F_N, F_W = [rk.Frame(OUTLINE[i], OUTLINE[(i + 1) % 4]) for i in range(4)]
# F_S u = x - 5.32 | F_E u = y | F_N u = 8.6 - x | F_W u = 6.0 - y
SINK_U = 1.8                            # centred under the window

def materials():
    return dict(
        wall=rk.mat("kitchen_wall", (0.86, 0.85, 0.80), 0.9),
        ceiling=rk.mat("kitchen_ceiling", (0.92, 0.92, 0.90), 0.9),
        floor=rk.tile("kitchen_tile", (0.80, 0.79, 0.76), (0.45, 0.45, 0.44), 0.30, 0.30, "xy"),
        trim=rk.mat("trim", (0.93, 0.93, 0.91), 0.5),
        steel=rk.mat("steel", (0.75, 0.75, 0.76), 0.25, 1.0),
        oak=rk.mat("table_oak", (0.62, 0.45, 0.28), 0.5),
        black=rk.mat("black_metal", (0.03, 0.03, 0.03), 0.4, 0.6),
        shade=rk.mat("shade_white", (0.92, 0.92, 0.90), 0.4),
    )

def style():
    return rk.Style(box_m=rk.mat("cab_green", (0.25, 0.33, 0.27), 0.5),
                    door_m=rk.mat("cab_green", (0.25, 0.33, 0.27), 0.5),
                    counter_m=rk.mat("quartz", (0.90, 0.89, 0.86), 0.2),
                    pull_m=rk.mat("brass", (0.80, 0.62, 0.32), 0.3, 1.0),
                    door="shaker", pull="bar",
                    splash_m=rk.tile("subway", (0.93, 0.93, 0.91), (0.75, 0.75, 0.73), 0.15, 0.075, "xz"),
                    splash_h=0.45)

def named(fn, *a, **kw):
    before = set(bpy.data.objects)
    out = fn(*a, **kw)
    for o in set(bpy.data.objects) - before:
        if not o.name.startswith((ROOM + "_", "ceiling_", "ground")):
            o.name = f"{ROOM}_{o.name}"
    return out

def build_asis():
    M, st = materials(), style()
    named(rk.shell, OUTLINE, CEILING, OPENINGS, M["wall"], M["floor"], M["ceiling"], base_m=M["trim"],
          shared=True, perimeter=pj.perimeter())
    for o in bpy.data.objects:
        if o.name == f"{ROOM}_ceiling":
            o.name = f"ceiling_{ROOM}"
    named(rk.window, F_N, *WINDOW, M["trim"], (2, 1))
    named(rk.door_casing, F_E, BACK_DOOR[0], BACK_DOOR[1], BACK_DOOR[3], M["trim"])
    named(rk.door_casing, F_W, TO_LIVING[0], TO_LIVING[1], TO_LIVING[3], M["trim"])
    named(F_E.box, "back_door", BACK_DOOR[0], BACK_DOOR[1], -0.09, -0.05, 0, BACK_DOOR[3], M["trim"])

    # north run (u from the NE corner going west): fridge | drawers | sink | dishwasher | doors
    named(rk.fridge, F_N, 0.05, 0.95, M["steel"], M["black"])
    named(rk.base_unit, F_N, st, 0.95, 1.35, "drawers")
    named(rk.base_unit, F_N, st, 1.35, 2.25, "sink")
    named(rk.dishwasher, F_N, 2.25, 2.85, M["steel"], M["black"])
    named(rk.base_unit, F_N, st, 2.85, 3.28)
    named(rk.countertop, F_N, 0.95, 3.28, st, sinks=((SINK_U, 0.76),), splash_top=WINDOW[2] - 0.02)
    named(rk.upper_unit, F_N, st, 0.05, 0.95, z0=1.85, z1=2.30)              # over the fridge
    named(rk.upper_unit, F_N, st, 2.55, 3.28)

    # south run (u from the SW corner going east): doors | range | drawers, hood over the range
    named(rk.base_unit, F_S, st, 0.30, 0.90)
    named(rk.range_unit, F_S, 0.90, 1.66, M["steel"], M["black"], style="glasstop")
    named(rk.base_unit, F_S, st, 1.66, 2.40, "drawers")
    named(rk.countertop, F_S, 0.30, 0.90, st)
    named(rk.countertop, F_S, 1.66, 2.40, st)
    named(rk.hood, F_S, 0.90, 1.66, 1.62, CEILING, M["steel"], style="chimney")
    named(rk.upper_unit, F_S, st, 0.30, 0.90)
    named(rk.upper_unit, F_S, st, 1.66, 2.40)
    # decluttered: the things that live on the counter stay (kettle, fruit bowl), loose stuff goes
    named(F_S.cyl, "kettle", 2.1, 0.35, 0.93, 1.15, 0.08, M["steel"])
    named(F_N.cyl, "fruit_bowl", 3.0, 0.35, 0.93, 1.0, 0.13, M["oak"])

    # dining: round table, four chairs, pendant over it
    tx, ty = 7.0, 3.0
    named(rk.round_table, tx, ty, 1.0, 0.75, M["oak"], M["black"])
    for a in (0, 90, 180, 270):
        named(rk.chair, tx - 0.62 * math.cos(math.radians(a)), ty - 0.62 * math.sin(math.radians(a)), a,
              M["oak"], style="windsor")
    lights()

def lights():
    pend = rk.pendant(7.0, 3.0, 1.55, "dome", materials()["shade"], watts=60, ceiling=CEILING)
    for x, y in ((6.0, 1.0), (7.9, 1.0), (6.0, 5.0), (7.9, 5.0)):
        rk.can_light(x, y, CEILING, watts=10)
    for o in bpy.data.objects:
        if o.name.startswith(("pendant_fitting", "can_lens")):
            o.name = "ceiling_" + o.name             # hidden with the ceiling in top views

CAMERAS = {
    # from the living-room opening, looking north-east at the sink wall
    "sink":     ((5.6, 2.6, 1.55), (8.0, 5.4, 1.05), 18),
    # from the back door, looking south-west at the range and the table
    "range":    ((8.3, 4.6, 1.55), (5.9, 0.6, 1.0), 18),
    "overhead": ((6.96, 3.0, 9.5), (6.96, 3.0, 0.0), 30),
}

FINAL_EXPOSURE = -0.2

def final_lighting():
    rk.daylight(sun_dir=(55, 0, 200), sun_strength=2.5, sky=(0.60, 0.72, 0.90), sky_strength=1.0)
    rk.window_glow(F_N, *WINDOW, watts=90)
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and not o.name.startswith(("sun", "winlight")):
            o.visible_glossy = False

def hide_for(cam_name):
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("ceiling"):
            o.hide_render = cam_name == "overhead"

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    final, test = "final" in args, "test" in args
    only = [a for a in args if a not in ("final", "test")]
    rk.reset()
    rk._mats.clear()
    build_asis()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _neighbours; _neighbours.build(ROOM)
    rk.use_cycles(64 if (test or not final) else 256, FINAL_EXPOSURE)
    final_lighting()
    os.makedirs(OUT, exist_ok=True)
    for name, c in CAMERAS.items():
        if only and name not in only:
            continue
        hide_for(name)
        cam = rk.camera(name, *c)
        if final:
            if test and name == "overhead":
                continue
            rk.render(cam, os.path.join(OUT, f"{'test' if test else 'final'}_{name}.jpg"),
                      (800, 500) if test else (2400, 1500))
        else:
            rk.render(cam, os.path.join(OUT, f"asis_{name}.jpg"))
    hide_for("")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{ROOM}_{'final' if final else 'asis'}.blend"))
