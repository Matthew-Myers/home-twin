# extract_one.py — evenly spaced stills from one video (any container Blender's sequencer reads).
# Run: blender -b -P scripts/extract_one.py -- "<video path>" <out folder> [count]
import bpy, os, sys

args = sys.argv[sys.argv.index("--") + 1:]
path, out = os.path.abspath(args[0]), os.path.abspath(args[1])  # relative video paths decode as 0x0
count = int(args[2]) if len(args) > 2 else 16
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
print(f"video: {n} frames, {w}x{h}")
for i in range(count):
    scene.frame_set(1 + int((n - 1) * (i + 0.5) / count))
    scene.render.filepath = os.path.join(out, f"{i:02d}.jpg")
    bpy.ops.render.render(write_still=True)
