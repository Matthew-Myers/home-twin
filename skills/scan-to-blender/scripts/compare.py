# compare.py - video still and render side by side at the same height, labelled, as one JPEG.
# Run: blender -b -P scripts/compare.py -- frames/<room>/08.jpg renders/<room>/asis_mirror.jpg renders/<room>/cmp_mirror.jpg [height]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgtools as it

args = it.script_args()
still, render, out = (os.path.abspath(p) for p in args[:3])
h = int(args[3]) if len(args) > 3 else 700
a, b = it.load(still, height=h), it.load(render, height=h)
gap = 10
c = it.canvas(a.shape[1] + gap + b.shape[1], h)
it.paste(c, a, 0, 0)
it.paste(c, b, a.shape[1] + gap, 0)
it.label(c, "video " + os.path.splitext(os.path.basename(still))[0], 0, 0)
it.label(c, "render " + os.path.splitext(os.path.basename(render))[0], a.shape[1] + gap, 0)
os.makedirs(os.path.dirname(out), exist_ok=True)
it.save(c, out)
print("compare:", out)
