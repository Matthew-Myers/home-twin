# extract_frames.py — pull evenly spaced stills from each room video into frames/<room>/.
# Uses Blender's video sequencer as the decoder, so no ffmpeg install is needed.
# Run: blender -b -P scripts/extract_frames.py
import bpy, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(ROOT, "source", "video")
FRAME_DIR = os.path.join(ROOT, "frames")
PER_VIDEO = 10      # stills per video
MAX_SIDE = 960      # long edge of each still, px

for path in sorted(glob.glob(os.path.join(VIDEO_DIR, "*.mp4"))):
    room = os.path.splitext(os.path.basename(path))[0].replace(" ", "-")
    out = os.path.join(FRAME_DIR, room)
    os.makedirs(out, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    seq = scene.sequence_editor_create()
    strip = seq.strips.new_movie(room, path, channel=1, frame_start=1)
    w, h = strip.elements[0].orig_width, strip.elements[0].orig_height
    n = strip.frame_final_duration

    k = MAX_SIDE / max(w, h)
    scene.render.resolution_x, scene.render.resolution_y = round(w * k), round(h * k)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 85
    print(f"{room}: {n} frames, {w}x{h}")

    for i in range(PER_VIDEO):
        scene.frame_set(1 + int((n - 1) * (i + 0.5) / PER_VIDEO))
        scene.render.filepath = os.path.join(out, f"{i:02d}.jpg")
        bpy.ops.render.render(write_still=True)
