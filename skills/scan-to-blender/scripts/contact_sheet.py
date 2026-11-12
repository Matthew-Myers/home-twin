# contact_sheet.py - grid of thumbnails from a frames folder, each labelled with its file name.
# Run: blender -b -P scripts/contact_sheet.py -- frames/<room> frames/sheet-<room>.jpg [cols] [thumb_width]
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgtools as it

args = it.script_args()
src, out = os.path.abspath(args[0]), os.path.abspath(args[1])
cols = int(args[2]) if len(args) > 2 else 6
tw = int(args[3]) if len(args) > 3 else 240
files = sorted(glob.glob(os.path.join(src, "*.jpg")) + glob.glob(os.path.join(src, "*.png")))
if not files:
    raise SystemExit(f"contact_sheet: no .jpg/.png in {src}")
thumbs = [it.load(f, width=tw) for f in files]
th = thumbs[0].shape[0]
rows = (len(files) + cols - 1) // cols
c = it.canvas(cols * tw, rows * th)
for i, (f, t) in enumerate(zip(files, thumbs)):
    x, y = (i % cols) * tw, (i // cols) * th
    it.paste(c, t[:th, :tw], x, y)
    it.label(c, os.path.splitext(os.path.basename(f))[0], x, y, scale=3)
os.makedirs(os.path.dirname(out), exist_ok=True)
it.save(c, out)
print(f"contact_sheet: {len(files)} frames -> {out}")
