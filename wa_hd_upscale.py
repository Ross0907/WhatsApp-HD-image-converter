"""
WhatsApp HD Upscaler
====================
Drop this exe next to your images and run it.
It upscales every image so the LONG side is at least 2560 px (Full HD+),
well above WhatsApp's HD threshold so the HD button always appears.

Originals are backed up to ./wa_originals/ before any change.
Already-large-enough images are skipped.
Files are always saved back to their ORIGINAL extension – no conversion.
"""

import sys
import shutil
from pathlib import Path
from PIL import Image, ImageFilter

# ── config ────────────────────────────────────────────────────────────────────
TARGET_LONG_SIDE  = 2560   # px – long side target (well above WhatsApp HD threshold of ~1600px)
SHARPEN_AFTER     = False   # light unsharp mask after upscale
JPEG_QUALITY      = 95     # 1-95; raised to 95 to preserve quality at 4K
BACKUP_DIR_NAME   = "wa_originals"

SUPPORTED_EXTS = {
    # JPEG family
    ".jpg", ".jpeg", ".jpe", ".jfif", ".jif",
    # PNG
    ".png",
    # GIF
    ".gif",
    # BMP
    ".bmp", ".dib",
    # TIFF
    ".tif", ".tiff",
    # WebP
    ".webp",
    # ICO / CUR
    ".ico", ".cur",
    # TGA
    ".tga", ".icb", ".vda", ".vst",
    # PPM / PGM / PBM / PNM
    ".ppm", ".pgm", ".pbm", ".pnm",
    # SGI / RGB
    ".sgi", ".rgb", ".rgba", ".bw",
    # PCX
    ".pcx",
    # PSD (read-only in Pillow)
    ".psd",
    # AVIF / HEIF / HEIC
    ".avif", ".heif", ".heic",
    # HDR
    ".exr", ".hdr",
    # DDS
    ".dds",
    # XBM
    ".xbm",
    # Sun Raster
    ".im",
}

# Maps extension → (pillow_save_format, required_mode_or_None, save_kwargs)
# Always write back to the SAME file with the SAME extension.
FORMAT_MAP = {
    ".jpg":  ("JPEG", "RGB",  {"quality": JPEG_QUALITY}),
    ".jpeg": ("JPEG", "RGB",  {"quality": JPEG_QUALITY}),
    ".jpe":  ("JPEG", "RGB",  {"quality": JPEG_QUALITY}),
    ".jfif": ("JPEG", "RGB",  {"quality": JPEG_QUALITY}),
    ".jif":  ("JPEG", "RGB",  {"quality": JPEG_QUALITY}),
    ".png":  ("PNG",  None,   {}),
    ".gif":  ("GIF",  "P",    {}),
    ".bmp":  ("BMP",  "RGB",  {}),
    ".dib":  ("BMP",  "RGB",  {}),
    ".tif":  ("TIFF", None,   {}),
    ".tiff": ("TIFF", None,   {}),
    ".webp": ("WEBP", None,   {"quality": JPEG_QUALITY}),
    ".ico":  ("ICO",  "RGBA", {}),
    ".cur":  ("ICO",  "RGBA", {}),
    ".tga":  ("TGA",  "RGB",  {}),
    ".icb":  ("TGA",  "RGB",  {}),
    ".vda":  ("TGA",  "RGB",  {}),
    ".vst":  ("TGA",  "RGB",  {}),
    ".ppm":  ("PPM",  "RGB",  {}),
    ".pgm":  ("PPM",  "L",    {}),
    ".pbm":  ("PPM",  "1",    {}),
    ".pnm":  ("PPM",  "RGB",  {}),
    ".sgi":  ("SGI",  "RGB",  {}),
    ".rgb":  ("SGI",  "RGB",  {}),
    ".rgba": ("SGI",  "RGBA", {}),
    ".bw":   ("SGI",  "L",    {}),
    ".pcx":  ("PCX",  "RGB",  {}),
    ".psd":  ("TIFF", None,   {}),   # Pillow can't write PSD; TIFF preserves pixels
    ".avif": ("AVIF", None,   {"quality": JPEG_QUALITY}),
    ".heif": ("HEIF", None,   {}),
    ".heic": ("HEIF", None,   {}),
    ".exr":  ("EXR",  None,   {}),
    ".hdr":  ("HDR",  "RGB",  {}),
    ".dds":  ("DDS",  None,   {}),
    ".xbm":  ("XBM",  None,   {}),
}
# ─────────────────────────────────────────────────────────────────────────────


def upscale_image(src: Path, backup_dir: Path) -> str:
    try:
        img = Image.open(src)
    except Exception as e:
        return f"  [SKIP] cannot open: {e}"

    w, h = img.size
    long_side = max(w, h)

    if long_side >= TARGET_LONG_SIDE:
        return f"  [SKIP] already {w}x{h} (long side {long_side}px >= {TARGET_LONG_SIDE}px)"

    # Back up original before touching it
    backup_dir.mkdir(exist_ok=True)
    shutil.copy2(src, backup_dir / src.name)

    # Scale so the LONG side hits TARGET_LONG_SIDE exactly
    scale = TARGET_LONG_SIDE / long_side
    new_w = round(w * scale)
    new_h = round(h * scale)

    ext = src.suffix.lower()
    save_fmt, target_mode, save_kw = FORMAT_MAP.get(ext, ("PNG", None, {}))

    # Multi-frame images (GIF, TIFF, APNG): grab first frame only
    try:
        img.seek(0)
    except (AttributeError, EOFError):
        pass

    # Mode conversion (only what the format strictly requires)
    if target_mode and img.mode != target_mode:
        if target_mode == "P":
            img = img.convert("RGB").quantize(colors=256)
        else:
            img = img.convert(target_mode)

    # Upscale with Bicubic resampling (fast, looks great at this resolution)
    img = img.resize((new_w, new_h), Image.BICUBIC)


    # Save back to the exact same path / extension
    try:
        img.save(src, save_fmt, **save_kw)
    except Exception:
        try:
            img.save(src, save_fmt)   # retry without extra kwargs
        except Exception as e:
            return f"  [FAIL] {e}"

    return f"  [OK]   {w}x{h}  ->  {new_w}x{new_h}  (long side now {max(new_w,new_h)}px)"


def main():
    base       = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    backup_dir = base / BACKUP_DIR_NAME

    images = sorted(
        p for p in base.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTS
        and p.resolve() != Path(sys.executable).resolve()
    )

    if not images:
        print("No supported images found in this folder.")
        input("\nPress Enter to exit...")
        return

    print("=" * 60)
    print(f"  WhatsApp HD Upscaler")
    print(f"  Target: long side >= {TARGET_LONG_SIDE}px (HD)")
    print(f"  Found {len(images)} image(s).  Backups -> ./{BACKUP_DIR_NAME}/")
    print("=" * 60 + "\n")

    ok = skip = fail = 0
    for img_path in images:
        result = upscale_image(img_path, backup_dir)
        tag = result.strip().split("]")[0].lstrip("[")
        if   tag == "OK":   ok   += 1
        elif tag == "SKIP": skip += 1
        else:               fail += 1
        print(f"{img_path.name}\n{result}\n")

    print("=" * 60)
    print(f"  Done.  Upscaled: {ok}  |  Skipped: {skip}  |  Failed: {fail}")
    print("  Open WhatsApp, attach these images, and the HD button")
    print("  should now appear before sending.")
    print("=" * 60)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()