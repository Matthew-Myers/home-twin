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
SUITE = ["home-project", "scan-to-floorplan", "room-rebuild", "renovation-concepts"]

LEVEL_STATES = ["draft", "approved"]
ROOM_STATES = ["planned", "modelled", "approved", "final"]
DETAIL_LEVELS = ["bare", "shelves cleared", "decluttered", "as-is"]
CONCEPT_STATES = ["draft", "shortlisted", "chosen", "rejected"]
SCOPES = ["refresh", "update", "rework"]       # see renovation-concepts/SKILL.md

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

def new_room(outline, ceiling, openings=None, kind="room", inferred=False, part_of=None):
    """outline: counter-clockwise interior corners [[x, y], ...]; openings: {edge: [[s0, s1, z0, z1], ...]}
    measured along each edge from its first corner (pj.opening() converts absolute coordinates).
    kind: "room" | "closet" | "stairs" | ...; inferred: the outline was NOT scanned but worked out
    (closets RoomPlan skipped); part_of: the room whose module builds this one (a closet built
    with its bedroom) - its status then follows that room's."""
    r = {"outline": [list(map(float, c)) for c in outline], "ceiling": ceiling,
         "openings": {str(k): v for k, v in (openings or {}).items()},
         "frames": None, "detail": None, "items": [],
         "module": None, "status": "planned", "notes": ""}
    if kind != "room":
        r["kind"] = kind
    if inferred:
        r["inferred"] = True
    if part_of:
        r["part_of"] = part_of
    return r

def opening(outline, edge, a, b, z0, z1):
    """[s0, s1, z0, z1] for an opening given by ABSOLUTE plan coordinates a..b along an edge (x for an
    east-west edge, y for a north-south one, as room_survey prints them). Counting from the edge's
    first corner by hand goes wrong on edges that run west or south; this doesn't."""
    (x0, y0), (x1, y1) = outline[edge], outline[(edge + 1) % len(outline)]
    dx, dy = x1 - x0, y1 - y0
    L = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / L, dy / L
    pts = [(c, y0 + (c - x0) * dy / dx) if abs(dx) >= abs(dy) else (x0 + (c - y0) * dx / dy, c) for c in (a, b)]
    s = sorted((px - x0) * ux + (py - y0) * uy for px, py in pts)
    return [round(s[0], 3), round(s[1], 3), z0, z1]

def perimeter(root=None, p=None):
    """interior faces of the level's outside walls, for rk.shell(shared=True): level.perimeter if
    set (any polygon, CCW), else the bounding rectangle of every room outline"""
    p = p or load(root)
    if p["level"].get("perimeter"):
        return [tuple(c) for c in p["level"]["perimeter"]]
    xs = [c[0] for r in p["rooms"].values() for c in r["outline"]]
    ys = [c[1] for r in p["rooms"].values() for c in r["outline"]]
    return [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]

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

def concept(room, cid, root=None):
    """a room's concept record (renovation-concepts), or None"""
    return load(root)["rooms"][room].get("concepts", {}).get(cid)

def set_concept(room, cid, root=None, skill="renovation-concepts", **fields):
    """create or update rooms.<room>.concepts.<cid>; status changes are logged to history"""
    p = load(root)
    cs = p["rooms"][room].setdefault("concepts", {})
    c = cs.setdefault(cid, {"title": cid, "scope": None, "idea": "", "changes": [], "keeps": [],
                            "module": None, "status": "draft", "notes": ""})
    if "status" in fields and fields["status"] not in CONCEPT_STATES:
        raise ValueError(f"concept status must be one of {CONCEPT_STATES}")
    if fields.get("status") and fields["status"] != c["status"]:
        log(p, f"{room}/{cid} -> {fields['status']}", skill)
    c.update(fields)
    save(p, root)
    return c

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

def _segments(p):
    """every door/opening (z0 == 0) as an absolute plan segment: (room, edge, (ax, ay), (bx, by))"""
    out = []
    for name, r in p["rooms"].items():
        pts = r["outline"]
        for k, ops in r.get("openings", {}).items():
            i = int(k)
            if i >= len(pts):
                continue
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 or 1
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            for s0, s1, z0, z1 in ops:
                if z0 == 0:
                    out.append((name, i, (x0 + ux * s0, y0 + uy * s0), (x0 + ux * s1, y0 + uy * s1)))
    return out

def _shared_door_problems(p, wall=(0.06, 0.20)):
    """a door in a wall shared with another room must be entered in BOTH rooms; warn when the room
    on the other side (its parallel wall face 0.06-0.20 m away, overlapping the door) has none"""
    out, segs = [], _segments(p)
    for name, i, a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = (dx * dx + dy * dy) ** 0.5
        if L < 1e-6:
            continue
        ux, uy = dx / L, dy / L
        nx, ny = uy, -ux                                   # outward (right of a CCW edge)
        for other, r in p["rooms"].items():
            if other == name:
                continue
            pts = r["outline"]
            for j in range(len(pts)):
                (px, py), (qx, qy) = pts[j], pts[(j + 1) % len(pts)]
                d0 = (px - a[0]) * nx + (py - a[1]) * ny
                d1 = (qx - a[0]) * nx + (qy - a[1]) * ny
                if not (wall[0] - 0.02 <= d0 <= wall[1] and abs(d0 - d1) < 0.02):
                    continue
                t0, t1 = sorted(((px - a[0]) * ux + (py - a[1]) * uy, (qx - a[0]) * ux + (qy - a[1]) * uy))
                if min(t1, L) - max(t0, 0) < 0.5 * L:      # that wall doesn't cover the door
                    continue
                mine = [s for s in segs if s[0] == other and s[1] == j]
                hit = any(min(L, max((s[2][0] - a[0]) * ux + (s[2][1] - a[1]) * uy,
                                     (s[3][0] - a[0]) * ux + (s[3][1] - a[1]) * uy))
                          - max(0, min((s[2][0] - a[0]) * ux + (s[2][1] - a[1]) * uy,
                                       (s[3][0] - a[0]) * ux + (s[3][1] - a[1]) * uy)) > 0.5 * L
                          for s in mine)
                if not hit:
                    out.append(f"{name}: door on edge {i} ({a[0]:.2f},{a[1]:.2f})-({b[0]:.2f},{b[1]:.2f}) has no "
                               f"matching opening in '{other}' edge {j} (shared wall: enter it in both rooms)")
    return out

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
        if r.get("part_of") and r["part_of"] not in p["rooms"]:
            out.append(f"{name}: part_of '{r['part_of']}' is not a room")
        for cid, c in r.get("concepts", {}).items():
            if c.get("status") not in CONCEPT_STATES:
                out.append(f"{name}/{cid}: concept status '{c.get('status')}' is not one of {CONCEPT_STATES}")
            if c.get("scope") and c["scope"] not in SCOPES:
                out.append(f"{name}/{cid}: scope '{c['scope']}' is not one of {SCOPES}")
            if c.get("status") != "draft" and r["status"] not in ("approved", "final"):
                out.append(f"{name}/{cid}: concepts past draft need the room approved first")
    b = p.get("brief")
    if b and b.get("scope") and b["scope"] not in SCOPES:
        out.append(f"brief: scope '{b['scope']}' is not one of {SCOPES}")
    out += _shared_door_problems(p)
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
        tag = (f"  [{r.get('kind', 'room')}" + (", inferred" if r.get("inferred") else "")
               + (f", part of {r['part_of']}" if r.get("part_of") else "") + "]") if (
               r.get("kind") or r.get("inferred") or r.get("part_of")) else ""
        st = p["rooms"][r["part_of"]]["status"] if r.get("part_of") in p["rooms"] else r["status"]
        print(f"  {name:<{w}}  {st:<9} detail={r.get('detail') or '-':<16} module={r.get('module') or '-'}{tag}")
        for cid, c in r.get("concepts", {}).items():
            print(f"  {'':<{w}}    concept {cid:<14} {c['status']:<11} {c.get('scope') or '-':<8} {c.get('title', '')}")
    if p.get("brief"):
        b = p["brief"]
        print(f"brief: scope={b.get('scope') or '-'}, style={b.get('style') or '-'}, "
              f"budget={b.get('budget') or '-'}")
    probs = check(p)
    print("checks: OK" if not probs else "checks:\n  " + "\n  ".join(probs))
    nxt = next_step(p)
    print(f"next: {nxt}")

def next_step(p):
    if not p["scan"].get("file"):
        return "scan-to-floorplan (no scan read yet)"
    if p["level"]["status"] != "approved":
        return "scan-to-floorplan (floorplan not approved yet)"
    own = {n: r for n, r in p["rooms"].items() if not r.get("part_of")}   # parts follow their room
    for name, r in own.items():
        if r["status"] in ("planned", "modelled"):
            return f"room-rebuild ({name} is {r['status']})"
    if any(r["status"] == "approved" for r in own.values()):
        return "room-rebuild (final renders for approved rooms)"
    if not p.get("brief"):
        return "all rooms final; renovation-concepts if a remodel is wanted (no design brief yet)"
    for name, r in p["rooms"].items():
        cs = r.get("concepts", {})
        if cs and not any(c["status"] == "chosen" for c in cs.values()):
            return f"renovation-concepts ({name}: no concept chosen yet)"
    return "all rooms final; renovation-concepts for any room without concepts"

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if not args or args[0] not in ("init", "sync", "status"):
        raise SystemExit("usage: project.py init|sync|status <project dir> [level name]")
    cmd, root = args[0], os.path.abspath(args[1] if len(args) > 1 else ".")
    {"init": lambda: init(root, args[2] if len(args) > 2 else None),
     "sync": lambda: sync(root), "status": lambda: status(root)}[cmd]()
