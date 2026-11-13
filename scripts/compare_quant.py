# Compare quantization levels at 1:1 (no downscale).
#
# The ComfyUI preview is ~768 px wide and hides exactly the artefacts that matter,
# so the only honest way to judge a render is to crop the centre of the full-size
# PNG and look at it 1:1.
#
#   python scripts/compare_quant.py [output_dir] [out_dir]
#
# Picks every output PNG whose filename contains q2k / q3km / q4km, crops the
# centre 1024x1024 region of each, and writes a side-by-side contact sheet.
import glob
import os
import sys

from PIL import Image, ImageDraw

DEFAULT_OUT = os.environ.get("COMFY_OUTPUT", "")
TAGS = ("q2k", "q3km", "q4km")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    if not out_dir:
        print("usage: python compare_quant.py <ComfyUI/output dir> [out_dir]")
        print("   or set COMFY_OUTPUT to the output directory")
        return 2
    here = os.path.dirname(os.path.abspath(__file__))
    save_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "samples")
    save_dir = os.path.abspath(save_dir)
    os.makedirs(save_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(out_dir, "*.png")), key=os.path.getmtime)
    print("found %d png in %s" % (len(files), out_dir))
    for f in files[-12:]:
        im = Image.open(f)
        print("  %-56s %-10s %6.2f MB" % (os.path.basename(f), "%dx%d" % im.size,
                                         os.path.getsize(f) / 1e6))

    crops = []
    for f in files:
        base = os.path.basename(f).lower()
        tag = next((t for t in TAGS if t in base), None)
        if tag is None:
            continue
        im = Image.open(f).convert("RGB")
        w, h = im.size
        c = 1024
        if w < c or h < c:
            print("  skip %s (smaller than 1024)" % base)
            continue
        box = ((w - c) // 2, (h - c) // 2, (w + c) // 2, (h + c) // 2)
        crops.append((tag, os.path.splitext(os.path.basename(f))[0], im.crop(box)))

    if not crops:
        print("no tagged outputs yet (need filenames containing q2k / q3km / q4km)")
        return 0

    for tag, name, crop in crops:
        p = os.path.join(save_dir, "crop_%s_%s.png" % (tag, name[-5:]))
        crop.save(p)
        print("wrote", p)

    sheet = Image.new("RGB", (1024 * len(crops), 1060), "black")
    d = ImageDraw.Draw(sheet)
    for i, (tag, name, crop) in enumerate(crops):
        sheet.paste(crop, (i * 1024, 30))
        d.text((i * 1024 + 8, 8), "%s  %s" % (tag.upper(), name), fill="white")
    p = os.path.join(save_dir, "cmp_sheet.png")
    sheet.save(p)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
