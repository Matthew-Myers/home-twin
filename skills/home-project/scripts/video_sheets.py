# video_sheets.py - every video in a folder -> evenly spaced stills + one contact sheet per video,
# in ONE Blender process (one launch per video adds up fast with 8+ walkthroughs).
# Run: blender -b -P scripts/video_sheets.py -- source/video frames [stills_per_video] [cols]
#   -> frames/<name>/00.jpg ... and frames/sheet-<name>.jpg
# <name> is the video's file name, or v1, v2, ... (in sorted order) for phone-style UUID names;
# the mapping is printed and written to frames/videos.txt for project.json's "videos".
import bpy, os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgtools as it

args = it.script_args()
if len(args) < 2:
    raise SystemExit("usage: video_sheets.py -- <video dir> <frames dir> [stills_per_video] [cols]")
src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
per = int(args[2]) if len(args) > 2 else 16
cols = int(args[3]) if len(args) > 3 else 6
MAX_SIDE, THUMB = 960, 240
UUIDISH = re.compile(r"^[0-9a-fA-F-]{20,}$")

videos = sorted(os.path.join(src, f) for f in os.listdir(src)      # one listing: Windows globs ignore case
                if os.path.splitext(f)[1].lower() in (".mp4", ".mov", ".m4v"))
if not videos:
    raise SystemExit(f"video_sheets: no videos in {src}")
lines = []
for n, path in enumerate(videos, 1):
    stem = os.path.splitext(os.path.basename(path))[0]
    name = f"v{n}" if UUIDISH.match(stem) else stem.replace(" ", "-")
    out = os.path.join(dst, name)
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    seq = scene.sequence_editor_create()
    strip = seq.strips.new_movie(name, path, channel=1, frame_start=1)
    w, h = strip.elements[0].orig_width, strip.elements[0].orig_height
    frames = strip.frame_final_duration
    k = MAX_SIDE / max(w, h)
    scene.render.resolution_x, scene.render.resolution_y = round(w * k), round(h * k)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 85
    files = []
    for i in range(per):
        f = 1 + int((frames - 1) * (i + 0.5) / per)
        scene.frame_set(f)
        scene.render.filepath = os.path.join(out, f"{i:02d}.jpg")
        bpy.ops.render.render(write_still=True)
        files.append(scene.render.filepath)
    thumbs = [it.load(f, width=THUMB) for f in files]
    th = thumbs[0].shape[0]
    rows = (len(files) + cols - 1) // cols
    c = it.canvas(cols * THUMB, rows * th)
    for i, t in enumerate(thumbs):
        x, y = (i % cols) * THUMB, (i // cols) * th
        it.paste(c, t[:th, :THUMB], x, y)
        it.label(c, f"{i:02d}", x, y, scale=3)
    it.save(c, os.path.join(dst, f"sheet-{name}.jpg"))
    orient = "portrait" if h > w else "landscape"
    lines.append(f"{name}\t{os.path.basename(path)}\t{frames} frames\t{w}x{h} {orient}")
    print(f"video_sheets: {lines[-1]}")
with open(os.path.join(dst, "videos.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"video_sheets: {len(videos)} videos -> {dst} (sheet-<name>.jpg each; mapping in videos.txt)")
