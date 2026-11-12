# imgtools.py - tiny image helpers for Blender's bundled Python (numpy + bpy, no PIL, any OS).
# Used by compare.py and contact_sheet.py. Images are numpy float arrays [h, w, 4], top row first.
import bpy, numpy as np

def load(path, height=None, width=None):
    """load an image, optionally resized to a height (or width), keeping its aspect"""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    if height:
        img.scale(max(1, round(w * height / h)), height)
    elif width:
        img.scale(width, max(1, round(h * width / w)))
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1].copy()

def canvas(w, h, rgb=(0, 0, 0)):
    a = np.ones((h, w, 4), dtype=np.float32)
    a[..., :3] = rgb
    return a

def paste(dst, src, x, y):
    h, w = src.shape[:2]
    dst[y:y + h, x:x + w] = src

def save(arr, path, quality=90):
    h, w = arr.shape[:2]
    img = bpy.data.images.new("out", w, h, alpha=False)
    img.pixels.foreach_set(arr[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = quality
    img.save()
    bpy.data.images.remove(img)

# 3x5 bitmap font: digits, upper-case letters and a little punctuation, enough for labels
_GLYPHS = {
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001010010",
    "8": "111101111101111", "9": "111101111001111", "A": "010101111101101", "B": "110101110101110",
    "C": "011100100100011", "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111", "J": "001001001101010",
    "K": "101101110101101", "L": "100100100100111", "M": "101111111101101", "N": "110101101101101",
    "O": "010101101101010", "P": "110101110100100", "Q": "010101101110011", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", "V": "101101101101010",
    "W": "101101111111101", "X": "101101010101101", "Y": "101101010010010", "Z": "111001010100111",
    "_": "000000000000111", "-": "000000111000000", ".": "000000000000010", ":": "000010000010000",
    " ": "000000000000000",
}

def label(dst, text, x, y, scale=4, fg=(1, 0.9, 0), bg=(0, 0, 0)):
    """draw text (upper-cased) at x, y with a black backing box"""
    text = text.upper()
    cw, chh = 4 * scale, 5 * scale
    w, h = len(text) * cw + scale * 2, chh + scale * 2
    y1, x1 = min(y + h, dst.shape[0]), min(x + w, dst.shape[1])
    dst[y:y1, x:x1, :3] = bg
    for i, ch in enumerate(text):
        g = _GLYPHS.get(ch, _GLYPHS["_"])
        for r in range(5):
            for c in range(3):
                if g[r * 3 + c] == "1":
                    yy, xx = y + scale + r * scale, x + scale + i * cw + c * scale
                    dst[yy:min(yy + scale, y1), xx:min(xx + scale, x1), :3] = fg

def script_args():
    import sys
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
