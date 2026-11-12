# living.py - living room of the made-up demo cottage, detail level "decluttered".
# In a real project: scripts/rooms/<room>.py, numbers from room_survey.py and the stills, with each
# camera reproducing a named still. Here everything is invented. Shows: shell from the survey outline,
# wall frames, roomkit furniture, a room-local helper (sofa), books as rows of blocks (lesson 2),
# real fixtures for light, CAMERAS + overhead, rough / test / final modes.
#
# Run: blender -b -P scripts/rooms/living.py [-- cam ...]          rough -> renders/living/asis_<cam>.jpg
#      blender -b -P scripts/rooms/living.py -- final test         800x500 test pass
#      blender -b -P scripts/rooms/living.py -- final              2400x1500 finals
# Live (MCP): importlib.reload(rk); importlib.reload(living); rk.reset(); living.build_asis()
import bpy, os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import roomkit as rk

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "renders", "living")
CEILING = 2.44
ROOM = "living"

# ---------------------------------------------------------------- geometry (plan metres)
OUTLINE = [(0.0, 0.0), (5.2, 0.0), (5.2, 6.0), (0.0, 6.0)]
DOOR = (0.3, 1.2, 0, 2.05)              # edge 0 (south), front door
WINDOW_S = (3.4, 4.8, 0.85, 2.05)       # edge 0 (south), picture window
TO_KITCHEN = (3.4, 4.6, 0, 2.10)        # edge 1 (east), cased opening
WINDOW_W = (2.0, 3.6, 0.85, 2.05)       # edge 3 (west)
OPENINGS = {0: [DOOR, WINDOW_S], 1: [TO_KITCHEN], 3: [WINDOW_W]}
F_S, F_E, F_N, F_W = [rk.Frame(OUTLINE[i], OUTLINE[(i + 1) % 4]) for i in range(4)]
# F_S u = x | F_E u = y | F_N u = 5.2 - x | F_W u = 6.0 - y; v always points into the room

def materials():
    return dict(
        wall=rk.mat("living_wall", (0.80, 0.78, 0.72), 0.9),
        ceiling=rk.mat("living_ceiling", (0.92, 0.92, 0.90), 0.9),
        floor=rk.plank_floor("living_oak", (0.60, 0.44, 0.28), (0.45, 0.31, 0.19)),
        trim=rk.mat("trim", (0.93, 0.93, 0.91), 0.5),
        sofa=rk.velvet("sofa_velvet", (0.16, 0.24, 0.30)),
        walnut=rk.mat("walnut", (0.28, 0.17, 0.10), 0.45),
        black=rk.mat("black_metal", (0.03, 0.03, 0.03), 0.4, 0.6),
        brass=rk.mat("brass", (0.80, 0.62, 0.32), 0.3, 1.0),
        rug=rk.mat("rug_wool", (0.74, 0.69, 0.60), 1.0),
        linen=rk.mat("linen_shade", (0.95, 0.92, 0.85), 0.8),
        screen=rk.mat("tv_screen", (0.01, 0.01, 0.012), 0.1),
        leaf=rk.mat("leaf", (0.10, 0.28, 0.08), 0.6),
        pot=rk.mat("terracotta", (0.62, 0.32, 0.20), 0.8),
    )

def named(fn, *a, **kw):
    """run a builder and prefix its new objects with the room name, so rooms assemble cleanly"""
    before = set(bpy.data.objects)
    out = fn(*a, **kw)
    for o in set(bpy.data.objects) - before:
        if not o.name.startswith((ROOM + "_", "ceiling_", "ground")):
            o.name = f"{ROOM}_{o.name}"
    return out

# ---------------------------------------------------------------- room-local helpers
def sofa(f, u0, u1, m, leg_m, depth=0.92, seat_h=0.44, back_h=0.82, arm_w=0.16):
    """three-seat sofa against a wall frame: plinth, seat cushions, back cushions, arms, legs"""
    for u in (u0 + 0.06, u1 - 0.08):
        for v in (0.06, depth - 0.08):
            f.box("sofa_leg", u, u + 0.02, v, v + 0.02, 0, 0.10, leg_m, 0.003)
    f.box("sofa_base", u0, u1, 0, depth, 0.10, seat_h - 0.12, m, 0.02)
    f.box("sofa_back", u0, u1, 0, 0.20, seat_h - 0.12, back_h, m, 0.04)
    for a, b in ((u0, u0 + arm_w), (u1 - arm_w, u1)):
        f.box("sofa_arm", a, b, 0, depth, seat_h - 0.12, seat_h + 0.18, m, 0.04)
    n = 3
    w = (u1 - u0 - 2 * arm_w) / n
    for i in range(n):
        a = u0 + arm_w + i * w
        f.box("sofa_seat", a + 0.005, a + w - 0.005, 0.20, depth, seat_h - 0.12, seat_h, m, 0.05)
        f.box("sofa_cushion", a + 0.01, a + w - 0.01, 0.18, 0.36, seat_h, back_h - 0.04, m, 0.06)

def books(f, u0, u1, z, m_list, depth=0.22, seed=0):
    """a shelf of books as a row of blocks: varied width, height and colour, nothing more"""
    rnd = random.Random(seed)
    u = u0
    while u < u1 - 0.03:
        w = rnd.uniform(0.02, 0.045)
        h = rnd.uniform(0.18, 0.28)
        f.box("book", u, min(u + w, u1), 0.04, depth, z, z + h, rnd.choice(m_list), 0.002)
        u += w + 0.002

# ---------------------------------------------------------------- the room
def build_asis():
    M = materials()
    named(rk.shell, OUTLINE, CEILING, OPENINGS, M["wall"], M["floor"], M["ceiling"], base_m=M["trim"])
    for o in bpy.data.objects:
        if o.name == f"{ROOM}_ceiling":
            o.name = f"ceiling_{ROOM}"
    named(rk.window, F_S, *WINDOW_S, M["trim"], (2, 1))
    named(rk.window, F_W, *WINDOW_W, M["trim"], (2, 1))
    named(rk.door_casing, F_S, DOOR[0], DOOR[1], DOOR[3], M["trim"])
    named(rk.door_casing, F_E, TO_KITCHEN[0], TO_KITCHEN[1], TO_KITCHEN[3], M["trim"])
    named(F_S.box, "front_door", DOOR[0], DOOR[1], -0.09, -0.05, 0, DOOR[3], rk.mat("door_red", (0.45, 0.08, 0.06), 0.4))

    named(rk.box, "threshold", 5.2, 3.4, -0.01, 5.32, 4.6, 0.0, M["floor"], 0)   # floor through the opening

    # seating group: sofa on the north wall, rug, coffee table, lounge chair by the west window
    named(sofa, F_N, 1.85, 4.05, M["sofa"], M["black"])                  # x 1.15-3.35
    named(rk.rug, 1.0, 2.2, 3.6, 4.9, M["rug"])
    named(rk.rect_table, 1.75, 3.35, 2.85, 3.95, 0.42, M["walnut"], M["black"])
    named(rk.lounge_chair, 0.85, 2.3, 45, M["walnut"], rk.mat("cognac", (0.45, 0.22, 0.10), 0.5), M["black"])
    named(rk.floor_lamp, 0.55, 5.55, M["linen"], M["brass"])

    # media wall: credenza + TV between the front door and the picture window
    named(rk.credenza, F_S, 1.5, 3.0, M["walnut"], M["walnut"], M["black"])
    named(F_S.box, "tv", 1.65, 2.85, 0.20, 0.24, 0.80, 1.47, M["screen"], 0.004)
    named(F_S.box, "tv_stand", 2.18, 2.32, 0.12, 0.30, 0.65, 0.82, M["black"], 0.002)

    # bookcase in the NE corner, books as blocks, one trailing plant (decluttered: what belongs there)
    zs = named(rk.etagere, F_N, 0.25, 1.15, M["black"], M["walnut"])
    covers = [rk.mat(f"book_{i}", c, 0.7) for i, c in enumerate(
        ((0.55, 0.12, 0.10), (0.12, 0.22, 0.35), (0.85, 0.80, 0.68), (0.20, 0.30, 0.18), (0.10, 0.10, 0.10)))]
    for k, z in enumerate(zs[:-1]):
        if k == 2:
            named(rk.trailing_vine, F_N, 0.7, z + 0.022, M["leaf"], M["pot"], shelf_d=0.34, seed=3)
            continue
        named(books, F_N, 0.30, 1.10 if k else 0.80, z + 0.022, covers, seed=k)

    lights()

def lights():
    """real fixtures: a flush mount in the middle and the floor lamp (in build_asis)"""
    rk.flush_light(2.6, 3.0, CEILING - 0.02, watts=60, color=(1.0, 0.82, 0.62))

CAMERAS = {
    # from the kitchen opening, looking south-west at the seating group and the west window
    "seating":  ((4.7, 3.9, 1.50), (0.6, 2.6, 0.95), 18),
    # from the front door, looking north-east: sofa, bookcase, kitchen opening
    "entry":    ((0.6, 0.7, 1.55), (4.6, 5.2, 1.0), 18),
    # cutaway from above (ceiling hidden) for the plausibility check
    "overhead": ((2.6, 3.0, 9.5), (2.6, 3.0, 0.0), 30),
}

FINAL_EXPOSURE = -0.2

def final_lighting():
    """Phase 6: daytime, daylight through the real windows (portals), warm fixtures on"""
    rk.daylight(sun_dir=(55, 0, 200), sun_strength=2.5, sky=(0.60, 0.72, 0.90), sky_strength=1.0)
    rk.window_glow(F_S, *WINDOW_S, watts=120)
    rk.window_glow(F_W, *WINDOW_W, watts=100)
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
    import _neighbours; _neighbours.build(ROOM)       # doorways show the real next room
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
