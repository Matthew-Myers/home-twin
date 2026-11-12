# board.py - before and every concept of a room from the same camera, labelled, as one JPEG per camera.
# Run: blender -b -P scripts/board.py -- <room> [rough|test|final] [concept ...]
#   no concepts named = every concept in project.json that isn't rejected, in project order
#   -> renders/<room>/concepts/board_<mode>_<cam>.jpg   (2 columns; before is always first)
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgtools as it, project as pj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = it.script_args()
if not args:
    raise SystemExit("usage: board.py -- <room> [rough|test|final] [concept ...]")
room = args[0]
mode = next((a for a in args[1:] if a in ("rough", "test", "final")), "test")
named = [a for a in args[1:] if a not in ("rough", "test", "final")]
concepts = pj.load(ROOT)["rooms"][room].get("concepts", {})
ids = named or [c for c, v in concepts.items() if v.get("status") != "rejected"]
base = os.path.join(ROOT, "renders", room, "concepts")

cams = sorted({os.path.basename(p)[len(mode) + 1:-4]
               for cid in ["before"] + ids for p in glob.glob(os.path.join(base, cid, f"{mode}_*.jpg"))})
if not cams:
    raise SystemExit(f"board: no {mode} renders under {base}")
H, GAP, COLS = 500, 10, 2
for cam in cams:
    tiles = []
    for cid in ["before"] + ids:
        p = os.path.join(base, cid, f"{mode}_{cam}.jpg")
        if os.path.exists(p):
            title = "before" if cid == "before" else f"{cid}: {concepts.get(cid, {}).get('title', '')}"
            tiles.append((it.load(p, height=H), title))
    if len(tiles) < 2:
        print(f"board: {cam} skipped (needs before + at least one concept)")
        continue
    w = max(t[0].shape[1] for t in tiles)
    rows = (len(tiles) + COLS - 1) // COLS
    c = it.canvas(COLS * w + (COLS - 1) * GAP, rows * H + (rows - 1) * GAP)
    for i, (img, title) in enumerate(tiles):
        x, y = (i % COLS) * (w + GAP), (i // COLS) * (H + GAP)
        it.paste(c, img, x, y)
        it.label(c, title[:40], x, y)
    out = os.path.join(base, f"board_{mode}_{cam}.jpg")
    it.save(c, out)
    print("board:", out)
