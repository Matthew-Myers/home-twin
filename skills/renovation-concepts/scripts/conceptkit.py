# conceptkit.py - renovation concepts as changes to a room as it is today.
#
# A concept module (scripts/concepts/<room>_<id>.py) never copies the room. It loads the approved
# room module, builds it as it is, removes / repaints / adds, then renders through the room's own
# CAMERAS, lighting and exposure, so "before" and "after" differ only by the concept:
#
#     import conceptkit as ck
#     def change(room):                       # room = the imported room module
#         ck.remove("kitchen_upper_*")
#         ck.swap_material("cab_green", rk.mat("cab_white", (0.9, 0.89, 0.85), 0.5))
#         ...
#     ck.run("kitchen", "bright", change)
#
# Run: blender -b -P scripts/concepts/kitchen_bright.py -- [test|final] [before] [cam ...]
#      (no mode = rough 64-sample 1600x1000; "before" renders the unchanged room with the same settings)
#      blender -b -P scripts/conceptkit.py -- list <room> [pattern]   object and material names to target
import bpy, os, sys, fnmatch, importlib.util

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
import roomkit as rk, project as pj

MODES = {  # mode: (samples, resolution, file prefix)
    "rough": (64, (1600, 1000), "rough"),
    "test": (64, (800, 500), "test"),
    "final": (256, (2400, 1500), "final"),
}

# ---------------------------------------------------------------- the room as it is
def load_room(room):
    """import the room's module (recorded in project.json) without running its __main__ block"""
    rel = pj.load(ROOT)["rooms"][room].get("module") or f"scripts/rooms/{room}.py"
    path = os.path.join(ROOT, rel)
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location(f"room_{room}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def build(room, neighbours=True):
    """fresh scene with the room as it is (and its neighbours seen through doorways)"""
    mod = load_room(room)
    rk.reset()
    rk._mats.clear()
    mod.build_asis()
    if neighbours:
        try:
            import _neighbours
            _neighbours.build(room)
        except ImportError:
            pass
    return mod

# ---------------------------------------------------------------- changes
def centre(o):
    """world-space centre of an object's bounding box (a light's location)"""
    if o.type != "MESH":
        return o.matrix_world.translation.copy()
    from mathutils import Vector
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(cs, Vector()) / 8

def find(*patterns, box=None, types=("MESH", "LIGHT", "CURVE", "EMPTY")):
    """objects whose name matches any fnmatch pattern ("kitchen_upper*"). box=(x0, y0, z0, x1, y1, z1)
    keeps only those whose centre lies inside it: room modules reuse names along every wall, so the
    box is how you pick "the uppers on the south wall" or "the chairs at the table"."""
    out = [o for o in bpy.data.objects if o.type in types
           and any(fnmatch.fnmatchcase(o.name, p) for p in patterns)]
    if box:
        x0, y0, z0, x1, y1, z1 = box
        out = [o for o in out if x0 <= centre(o).x <= x1 and y0 <= centre(o).y <= y1
               and z0 <= centre(o).z <= z1]
    return out

def _check(patterns, hits, what):
    for p in patterns:
        if not any(fnmatch.fnmatchcase(o.name, p) for o in hits):
            raise SystemExit(f"conceptkit.{what}: '{p}' matched nothing "
                             f"(conceptkit.py -- list <room> shows the names and centres)")

def remove(*patterns, box=None, keep=()):
    """delete matching objects (except those matching keep); a pattern that matches nothing stops
    the script, so a renamed object can't silently leave the old version in the render"""
    hits = find(*patterns, box=box)
    _check(patterns, hits, "remove")
    gone = [o for o in hits if not any(fnmatch.fnmatchcase(o.name, k) for k in keep)]
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)

def swap_material(old, new):
    """replace a material everywhere it is used (old: name or fnmatch pattern; new: a material).
    The quickest way to repaint every cabinet, wall or floor that shares a finish."""
    n = 0
    for o in bpy.data.objects:
        for s in getattr(o, "material_slots", []):
            if s.material and fnmatch.fnmatchcase(s.material.name, old):
                s.material = new
                n += 1
    if not n:
        raise SystemExit(f"conceptkit.swap_material: no object uses a material matching '{old}'")
    return n

def recolor(patterns, new, box=None):
    """give matching objects a new material (all slots)"""
    patterns = (patterns,) if isinstance(patterns, str) else tuple(patterns)
    hits = find(*patterns, box=box, types=("MESH", "CURVE"))
    _check(patterns, hits, "recolor")
    for o in hits:
        if not o.material_slots:
            o.data.materials.append(new)
        for s in o.material_slots:
            s.material = new
    return len(hits)

def move(patterns, dx=0.0, dy=0.0, dz=0.0, box=None):
    """shift matching objects (and lights) by a world offset"""
    patterns = (patterns,) if isinstance(patterns, str) else tuple(patterns)
    hits = find(*patterns, box=box)
    _check(patterns, hits, "move")
    for o in hits:
        o.location.x += dx; o.location.y += dy; o.location.z += dz
    return len(hits)

def add(prefix, fn, *a, **kw):
    """call a roomkit builder and prefix what it creates: "ceiling_" for anything on the ceiling
    (hidden with it in overhead views), "<room>_" for the rest, so later concepts can target it"""
    before = set(bpy.data.objects)
    out = fn(*a, **kw)
    for o in set(bpy.data.objects) - before:
        if not o.name.startswith(prefix):
            o.name = prefix + o.name
    return out

def extent(*patterns, box=None):
    """world bounding box (x0, y0, z0, x1, y1, z1) of the matching meshes together"""
    from mathutils import Vector
    hits = find(*patterns, box=box, types=("MESH",))
    _check(patterns, hits, "extent")
    cs = [o.matrix_world @ Vector(c) for o in hits for c in o.bound_box]
    return (min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs),
            max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs))

def clearance(a, b):
    """plan distance (m) between two extents, e.g. an island and the counter run behind it:
    clearance(extent("kitchen_island*"), extent("kitchen_counter*", box=SOUTH)).
    0 means they overlap in plan. Compare with reference/design-rules.md, and print it in the write-up."""
    dx = max(0.0, max(a[0], b[0]) - min(a[3], b[3]))
    dy = max(0.0, max(a[1], b[1]) - min(a[4], b[4]))
    return (dx * dx + dy * dy) ** 0.5

def listing(pattern="*"):
    """object names grouped, with materials: what a concept can target"""
    rows = {}
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if not fnmatch.fnmatchcase(o.name, pattern):
            continue
        mats = sorted({s.material.name for s in getattr(o, "material_slots", []) if s.material})
        c = centre(o)
        rows.setdefault(o.type, []).append(f"{o.name:<28} at ({c.x:5.2f}, {c.y:5.2f}, {c.z:4.2f})"
                                           + (f"  [{', '.join(mats)}]" if mats else ""))
    for t, names in rows.items():
        print(f"-- {t} ({len(names)})")
        for n in names:
            print("  ", n)

# ---------------------------------------------------------------- render
def out_dir(room, cid):
    return os.path.join(ROOT, "renders", room, "concepts", cid)

def run(room, cid, change, info=None, extra_cameras=None, lighting=None):
    """build the room, apply change(room_module) unless 'before', light it as the room does, then
    render every camera (or those named on the command line).
    info: the concept's record for project.json (title, scope, idea, changes, keeps), written on every
    run so the module stays the one source; status is left alone (the skill sets it on the user's word).
    extra_cameras: {name: (eye, target, lens)} for views only this concept needs.
    lighting(room_module): replaces the room's final_lighting (e.g. an evening variant)."""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = "final" if "final" in args else "test" if "test" in args else "rough"
    before = "before" in args
    only = [a for a in args if a not in ("final", "test", "before")]
    samples, res, prefix = MODES[mode]

    mod = build(room)
    if not before:
        change(mod)
        script = sys.argv[sys.argv.index("-P") + 1] if "-P" in sys.argv else None
        rec = dict(info or {})
        if script:
            rec["module"] = os.path.relpath(os.path.abspath(script), ROOT).replace("\\", "/")
        pj.set_concept(room, cid, ROOT, **rec)
    rk.use_cycles(samples, getattr(mod, "FINAL_EXPOSURE", 0.0))
    if lighting:
        lighting(mod)
    elif hasattr(mod, "final_lighting"):
        mod.final_lighting()

    cams = dict(getattr(mod, "CAMERAS", {}))
    cams.update(extra_cameras or {})
    name = "before" if before else cid
    out = out_dir(room, name)
    os.makedirs(out, exist_ok=True)
    hide = getattr(mod, "hide_for", lambda n: None)
    for cname, c in cams.items():
        if only and cname not in only:
            continue
        if mode == "test" and cname == "overhead" and not only:
            continue
        hide(cname)
        cam = rk.camera(cname, *c)
        rk.render(cam, os.path.join(out, f"{prefix}_{cname}.jpg"), res)
    hide("")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{room}_{name}.blend"))
    print(f"conceptkit: {room}/{name} {mode} -> {out}")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) < 2 or args[0] != "list":
        raise SystemExit("usage: conceptkit.py -- list <room> [pattern]")
    build(args[1], neighbours=False)
    listing(args[2] if len(args) > 2 else "*")
