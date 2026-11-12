# project.py - the shared project file (project.json) for the home-scan suite, and a small CLI.
#
# In Blender scripts (copied into <project>/scripts/):
#     import project as pj
#     OUTLINE, OPENINGS, CEILING = pj.geometry("living")      # the one source of room geometry
#     pj.set_status("living", "modelled")
#
# CLI (Blender's Python or any Python 3.8+; run it from the SKILL folder, not a project copy):
#     blender -b -P <home-project>/scripts/project.py -- init   <project dir> [level name]
#     blender -b -P <home-project>/scripts/project.py -- sync   <project dir>   re-copy suite scripts
#     blender -b -P <home-project>/scripts/project.py -- status <project dir>   phases + checks
# (or: python project.py init <dir> ...)
import json, os, sys, shutil, datetime

FORMAT = 1
HERE = os.path.dirname(os.path.abspath(__file__))
# skills whose scripts/ are copied into a project, in this order (later ones win on a clash)
SUITE = ["home-project", "scan-to-floorplan", "room-rebuild"]

LEVEL_STATES = ["draft", "approved"]
ROOM_STATES = ["planned", "modelled", "approved", "final"]
DETAIL_LEVELS = ["bare", "shelves cleared", "decluttered", "as-is"]

def _default_root():
    """a copy in <project>/scripts/ -> <project>"""
    return os.path.dirname(HERE)

def path(root=None):
    return os.path.join(root or _default_root(), "project.json")

def load(root=None):
    with open(path(root), encoding="utf-8") as f:
        return json.load(f)

def save(p, root=None):
    with open(path(root), "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)
        f.write("\n")

def log(p, event, skill=None):
    p.setdefault("history", []).append(
        {"date": datetime.date.today().isoformat(), "skill": skill, "event": event})

def new(name):
    return {
        "format": FORMAT,
        "name": name,
        "coords": "metres from the level's south-west corner; x east, y north, z = 0 at the floor",
        "scan": {"file": None, "k": None, "footprint_m": None},
        "videos": [],
        "level": {"ceiling": None, "script": "scripts/level.py", "status": "draft"},
        "rooms": {},
        "history": [],
    }

def new_room(outline, ceiling, openings=None):
    """outline: counter-clockwise interior corners [[x, y], ...]; openings: {edge: [[s0, s1, z0, z1], ...]}
    measured along each edge from its first corner"""
    return {"outline": [list(map(float, c)) for c in outline], "ceiling": ceiling,
            "openings": {str(k): v for k, v in (openings or {}).items()},
            "frames": None, "detail": None, "items": [],
            "module": None, "status": "planned", "notes": ""}

# ---------------------------------------------------------------- used by Blender scripts
def geometry(room, root=None):
    """(outline as tuples, openings with int edge keys, ceiling) for rk.shell()"""
    r = load(root)["rooms"][room]
    outline = [tuple(c) for c in r["outline"]]
    openings = {int(k): [tuple(o) for o in v] for k, v in r.get("openings", {}).items()}
    return outline, openings, r["ceiling"]

def set_status(room, status, root=None, skill=None):
    p = load(root)
    states = LEVEL_STATES if room == "level" else ROOM_STATES
    if status not in states:
        raise ValueError(f"{room}: status must be one of {states}")
    (p["level"] if room == "level" else p["rooms"][room])["status"] = status
    log(p, f"{room} -> {status}", skill)
    save(p, root)

def require(room, at_least, root=None):
    """stop unless the room (or 'level') has reached a state, e.g. require('kitchen', 'approved')"""
    p = load(root)
    states = LEVEL_STATES if room == "level" else ROOM_STATES
    cur = (p["level"] if room == "level" else p["rooms"][room])["status"]
    if states.index(cur) < states.index(at_least):
        raise SystemExit(f"{room} is '{cur}', needs '{at_least}' first")

# ---------------------------------------------------------------- checks
def _area2(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))

def check(p):
    """cheap sanity checks; returns a list of problems"""
    out = []
    for name, r in p.get("rooms", {}).items():
        pts = r["outline"]
        if len(pts) < 3:
            out.append(f"{name}: outline needs 3+ corners")
            continue
        if _area2(pts) <= 0:
            out.append(f"{name}: outline is clockwise (must be counter-clockwise)")
        for k, ops in r.get("openings", {}).items():
            i = int(k)
            if i >= len(pts):
                out.append(f"{name}: opening on edge {i}, but the outline has {len(pts)} edges")
                continue
            a, b = pts[i], pts[(i + 1) % len(pts)]
            length = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            for s0, s1, z0, z1 in ops:
                if not (0 <= s0 < s1 <= length + 1e-6):
                    out.append(f"{name}: edge {i} opening {s0}-{s1} outside 0-{length:.2f}")
                if not (0 <= z0 < z1 <= (r.get("ceiling") or 99) + 1e-6):
                    out.append(f"{name}: edge {i} opening height {z0}-{z1} outside floor-ceiling")
        if r.get("detail") and r["detail"] not in DETAIL_LEVELS:
            out.append(f"{name}: detail '{r['detail']}' is not one of {DETAIL_LEVELS}")
    return out

# ---------------------------------------------------------------- CLI
def _skills_dir():
    return os.path.dirname(os.path.dirname(HERE))      # <skills>/home-project/scripts -> <skills>

def sync(root):
    """copy every suite skill's scripts/ into <root>/scripts/; never touches level.py or room modules"""
    copied = []
    for skill in SUITE:
        src = os.path.join(_skills_dir(), skill, "scripts")
        if not os.path.isdir(src):
            print(f"project: skill '{skill}' not found next to home-project, skipped")
            continue
        for dirpath, _, files in os.walk(src):
            for fn in files:
                if not fn.endswith(".py") or "__pycache__" in dirpath:
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), src)
                dst = os.path.join(root, "scripts", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(dirpath, fn), dst)
                copied.append(rel)
    print(f"project: {len(set(copied))} suite scripts copied into {os.path.join(root, 'scripts')}")

def init(root, name=None):
    for d in ("source/scan", "source/video", "frames", "scripts/rooms", "renders", "assets"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    if os.path.exists(path(root)):
        print("project: project.json already exists, left as is")
    else:
        p = new(name or os.path.basename(os.path.abspath(root)))
        log(p, "project created", "home-project")
        save(p, root)
        print(f"project: created {path(root)}")
    sync(root)

def status(root):
    p = load(root)
    lv = p["level"]
    print(f"{p['name']}: level {lv['status']}, ceiling {lv.get('ceiling')} m, scan {p['scan'].get('file')}")
    w = max([len(n) for n in p["rooms"]] + [4])
    for name, r in p["rooms"].items():
        print(f"  {name:<{w}}  {r['status']:<9} detail={r.get('detail') or '-':<16} module={r.get('module') or '-'}")
    probs = check(p)
    print("checks: OK" if not probs else "checks:\n  " + "\n  ".join(probs))
    nxt = next_step(p)
    print(f"next: {nxt}")

def next_step(p):
    if not p["scan"].get("file"):
        return "scan-to-floorplan (no scan read yet)"
    if p["level"]["status"] != "approved":
        return "scan-to-floorplan (floorplan not approved yet)"
    for name, r in p["rooms"].items():
        if r["status"] in ("planned", "modelled"):
            return f"room-rebuild ({name} is {r['status']})"
    if any(r["status"] == "approved" for r in p["rooms"].values()):
        return "room-rebuild (final renders for approved rooms)"
    return "all rooms final"

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if not args or args[0] not in ("init", "sync", "status"):
        raise SystemExit("usage: project.py init|sync|status <project dir> [level name]")
    cmd, root = args[0], os.path.abspath(args[1] if len(args) > 1 else ".")
    {"init": lambda: init(root, args[2] if len(args) > 2 else None),
     "sync": lambda: sync(root), "status": lambda: status(root)}[cmd]()
