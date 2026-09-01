"""WhatsApp HD image upscaler.

Default behavior:
- Put the executable in a folder containing images and run it.
- Images whose long side is below TARGET_LONG_SIDE are upscaled in place.
- The first original copy is preserved in ./wa_originals/.
- The program exits automatically when processing is complete.

The script/executable also accepts files or folders as command-line arguments,
which means files/folders can be dragged onto the executable in Windows.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

TARGET_LONG_SIDE = 2560
JPEG_QUALITY = 95
BACKUP_DIR_NAME = "wa_originals"
LOG_FILE_NAME = "wa_hd_upscale.log"
SHARPEN_AFTER = False

# Formats that can safely be rewritten without intentionally changing the
# file's container/extension. Multi-frame files are skipped to avoid silently
# destroying animation/pages.
FORMAT_MAP: dict[str, tuple[str, str | None, dict[str, object]]] = {
    ".jpg": ("JPEG", "RGB", {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True}),
    ".jpeg": ("JPEG", "RGB", {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True}),
    ".jpe": ("JPEG", "RGB", {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True}),
    ".jfif": ("JPEG", "RGB", {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True}),
    ".jif": ("JPEG", "RGB", {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True}),
    ".png": ("PNG", None, {"optimize": True}),
    ".gif": ("GIF", "P", {}),
    ".bmp": ("BMP", "RGB", {}),
    ".dib": ("BMP", "RGB", {}),
    ".tif": ("TIFF", None, {}),
    ".tiff": ("TIFF", None, {}),
    ".webp": ("WEBP", None, {"quality": JPEG_QUALITY, "method": 6}),
    ".tga": ("TGA", "RGB", {}),
    ".icb": ("TGA", "RGB", {}),
    ".vda": ("TGA", "RGB", {}),
    ".vst": ("TGA", "RGB", {}),
    ".ppm": ("PPM", "RGB", {}),
    ".pgm": ("PPM", "L", {}),
    ".pbm": ("PPM", "1", {}),
    ".pnm": ("PPM", "RGB", {}),
    ".sgi": ("SGI", "RGB", {}),
    ".rgb": ("SGI", "RGB", {}),
    ".rgba": ("SGI", "RGBA", {}),
    ".bw": ("SGI", "L", {}),
    ".pcx": ("PCX", "RGB", {}),
    ".avif": ("AVIF", None, {"quality": JPEG_QUALITY}),
}

# Recognized image extensions that are deliberately not rewritten because the
# original implementation could corrupt semantics (e.g. PSD->TIFF with a PSD
# extension, or ICO/CUR multi-size data loss) or because Pillow commonly lacks
# a safe matching writer.
SKIP_EXTS = {
    ".psd", ".heif", ".heic", ".ico", ".cur", ".exr", ".hdr", ".dds", ".xbm", ".im"
}

CANDIDATE_EXTS = set(FORMAT_MAP) | SKIP_EXTS


@dataclass(frozen=True)
class Result:
    status: str
    message: str


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def silent_runtime() -> bool:
    # PyInstaller --noconsole/--windowed normally sets stdout/stderr to None.
    return getattr(sys, "frozen", False) and sys.stdout is None


def emit(lines: list[str], text: str, quiet: bool) -> None:
    lines.append(text)
    if not quiet and sys.stdout is not None:
        print(text)


def collect_images(paths: list[Path], recursive: bool) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()

    def add_file(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        if resolved in seen or not path.is_file():
            return
        if path.suffix.lower() not in CANDIDATE_EXTS:
            return
        seen.add(resolved)
        found.append(path)

    for item in paths:
        if item.is_file():
            add_file(item)
            continue
        if not item.is_dir():
            continue

        iterator = item.rglob("*") if recursive else item.iterdir()
        for child in iterator:
            # Never process backup copies when recursion is enabled.
            if BACKUP_DIR_NAME in child.parts:
                continue
            add_file(child)

    return sorted(found, key=lambda p: str(p).lower())


def backup_original(src: Path) -> tuple[bool, str | None]:
    """Create a non-destructive first-original backup.

    Existing backups are intentionally never overwritten. This prevents a
    later run with a larger target from replacing the true original with an
    already-upscaled version.
    """
    backup_dir = src.parent / BACKUP_DIR_NAME
    backup_path = backup_dir / src.name
    try:
        backup_dir.mkdir(exist_ok=True)
        if not backup_path.exists():
            shutil.copy2(src, backup_path)
        return True, None
    except Exception as exc:
        return False, str(exc)


def metadata_kwargs(img: Image.Image, save_format: str) -> dict[str, object]:
    result: dict[str, object] = {}

    icc = img.info.get("icc_profile")
    if icc and save_format in {"JPEG", "PNG", "WEBP", "TIFF"}:
        result["icc_profile"] = icc

    dpi = img.info.get("dpi")
    if dpi and save_format in {"JPEG", "PNG", "TIFF"}:
        result["dpi"] = dpi

    if save_format in {"JPEG", "WEBP", "TIFF"}:
        try:
            exif = img.getexif()
            if exif:
                result["exif"] = exif.tobytes()
        except Exception:
            pass

    return result


def convert_mode(img: Image.Image, target_mode: str | None) -> Image.Image:
    if target_mode is None or img.mode == target_mode:
        return img

    if target_mode == "P":
        return img.convert("RGBA" if "A" in img.getbands() else "RGB").quantize(colors=256)

    if target_mode == "RGB" and "A" in img.getbands():
        # A transparent source cannot be represented in RGB. Composite onto a
        # white background rather than dropping alpha to black unexpectedly.
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")

    return img.convert(target_mode)


def temp_path_for(src: Path) -> Path:
    candidate = src.with_name(f".{src.stem}.wa_hd_tmp{src.suffix}")
    counter = 1
    while candidate.exists():
        candidate = src.with_name(f".{src.stem}.wa_hd_tmp_{counter}{src.suffix}")
        counter += 1
    return candidate


def save_atomic(
    img: Image.Image,
    src: Path,
    save_format: str,
    save_kwargs: dict[str, object],
    fallback_kwargs: dict[str, object],
) -> tuple[bool, str | None]:
    tmp = temp_path_for(src)
    try:
        try:
            img.save(tmp, save_format, **save_kwargs)
        except Exception:
            # Metadata support differs between Pillow encoders/platforms. Retry
            # with only the essential format settings, still writing to temp.
            if tmp.exists():
                tmp.unlink()
            img.save(tmp, save_format, **fallback_kwargs)

        # Verify that Pillow can reopen the produced file before replacing the
        # original. This makes interrupted/failed writes much less destructive.
        with Image.open(tmp) as check:
            check.verify()

        try:
            shutil.copystat(src, tmp)
        except OSError:
            pass

        os.replace(tmp, src)
        return True, None
    except Exception as exc:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False, str(exc)


def upscale_image(src: Path, target_long_side: int) -> Result:
    ext = src.suffix.lower()

    if ext in SKIP_EXTS:
        return Result("SKIP", f"unsafe/read-only rewrite format: {ext}")

    mapping = FORMAT_MAP.get(ext)
    if mapping is None:
        return Result("SKIP", f"unsupported extension: {ext}")

    save_format, target_mode, base_save_kwargs = mapping

    # Make sure the current Pillow build actually has the required writer.
    save_formats = getattr(upscale_image, "_save_formats", None)
    if save_formats is None:
        Image.init()
        save_formats = set(Image.SAVE)
        setattr(upscale_image, "_save_formats", save_formats)
    if save_format not in save_formats:
        return Result("SKIP", f"this Pillow build cannot write {save_format}")

    try:
        with Image.open(src) as opened:
            frame_count = getattr(opened, "n_frames", 1)
            if frame_count > 1:
                return Result("SKIP", f"multi-frame image ({frame_count} frames/pages) left unchanged")

            # Apply EXIF orientation before measuring/resizing so portrait phone
            # photos get the expected dimensions and orientation.
            img = ImageOps.exif_transpose(opened)
            img.load()

            w, h = img.size
            long_side = max(w, h)
            if long_side >= target_long_side:
                return Result("SKIP", f"already {w}x{h} (long side {long_side}px >= {target_long_side}px)")

            ok, error = backup_original(src)
            if not ok:
                return Result("FAIL", f"backup failed; original was not changed: {error}")

            scale = target_long_side / long_side
            new_w = max(1, round(w * scale))
            new_h = max(1, round(h * scale))

            metadata = metadata_kwargs(img, save_format)

            # LANCZOS costs a little more CPU than bicubic but produces a better
            # general-purpose photographic upscale.
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            if SHARPEN_AFTER:
                img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=3))

            img = convert_mode(img, target_mode)
            save_kwargs = dict(base_save_kwargs)
            save_kwargs.update(metadata)

            ok, error = save_atomic(img, src, save_format, save_kwargs, dict(base_save_kwargs))
            if not ok:
                return Result("FAIL", f"save failed; original remains available in backup: {error}")

            return Result("OK", f"{w}x{h} -> {new_w}x{new_h}")

    except Exception as exc:
        return Result("SKIP", f"cannot open/process: {exc}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upscale smaller images for WhatsApp HD uploads.")
    parser.add_argument("paths", nargs="*", help="Image files or folders. Defaults to the executable/script folder.")
    parser.add_argument("--target", type=int, default=TARGET_LONG_SIDE, help="Target long side in pixels (default: 2560).")
    parser.add_argument("--recursive", action="store_true", help="Scan folders recursively.")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output; a log is written instead.")
    return parser.parse_args(argv)


def write_log(lines: list[str], location: Path) -> None:
    try:
        location.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.target < 1:
        if sys.stderr is not None:
            print("ERROR: --target must be at least 1.", file=sys.stderr)
        return 2

    base = runtime_dir()
    requested = [Path(p).expanduser() for p in args.paths] if args.paths else [base]
    quiet = bool(args.quiet or silent_runtime())
    lines: list[str] = []

    emit(lines, f"WhatsApp HD Upscaler - {datetime.now().isoformat(timespec='seconds')}", quiet)
    emit(lines, f"Target long side: {args.target}px", quiet)

    images = collect_images(requested, args.recursive)
    if not images:
        emit(lines, "No supported images found.", quiet)
        if quiet:
            write_log(lines, base / LOG_FILE_NAME)
        return 0

    emit(lines, f"Found {len(images)} image(s).", quiet)

    ok_count = skip_count = fail_count = 0
    for path in images:
        result = upscale_image(path, args.target)
        if result.status == "OK":
            ok_count += 1
        elif result.status == "SKIP":
            skip_count += 1
        else:
            fail_count += 1
        emit(lines, f"[{result.status}] {path}: {result.message}", quiet)

    emit(lines, f"Done. Upscaled: {ok_count} | Skipped: {skip_count} | Failed: {fail_count}", quiet)

    if quiet:
        write_log(lines, base / LOG_FILE_NAME)

    # No input()/pause here: both script and console EXE exit automatically.
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
