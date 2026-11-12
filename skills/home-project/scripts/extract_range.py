# extract_range.py - dense stills from part of a video, to settle a correction (more angles on one spot).
# Run: blender -b -P scripts/extract_range.py -- "<video>" <out folder> <first frame> <last frame> [step]
# Frame numbers: still k of extract_one.py (count N, n frames) sits at frame 1 + int((n-1)*(k+0.5)/N);
# pull e.g. +/-80 frames around the stills that show the spot. Files are named f<frame>.jpg.
import bpy, os, sys

args = sys.argv[sys.argv.index("--") + 1:]
path, out = os.path.abspath(args[0]), os.path.abspath(args[1])   # relative paths decode as 0x0
first, last = int(args[2]), int(args[3])
step = int(args[4]) if len(args) > 4 else 15
MAX_SIDE = 960
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
seq = scene.sequence_editor_create()
strip = seq.strips.new_movie("v", path, channel=1, frame_start=1)
w, h = strip.elements[0].orig_width, strip.elements[0].orig_height
n = strip.frame_final_duration
k = MAX_SIDE / max(w, h)
scene.render.resolution_x, scene.render.resolution_y = round(w * k), round(h * k)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 85
print(f"video: {n} frames, {w}x{h}; extracting {first}-{last} step {step}")
for f in range(max(1, first), min(n, last) + 1, step):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(out, f"f{f:05d}.jpg")
    bpy.ops.render.render(write_still=True)
