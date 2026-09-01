# WhatsApp HD Upscaler

A small Windows/Python utility that enlarges smaller images to a 2560 px long side so they can be uploaded using WhatsApp's HD image option. Originals are preserved before any in-place change.

## Windows executables

Two builds are supported:

- `wa_hd_upscale.exe` — shows console progress and **exits automatically as soon as processing finishes**.
- `wa_hd_upscale_silent.exe` — **no console/window**. It runs silently, exits when finished, and writes `wa_hd_upscale.log` beside the executable.

Download the prebuilt exe: [here](https://github.com/Ross0907/WhatsApp-HD-image-converter/releases/tag/v1.1)

### Normal use

Put either executable in the folder containing the images and double-click it.

You can also drag image files or folders onto the executable. Folder arguments are scanned non-recursively by default.

Every image that is changed gets an original copy in a `wa_originals` folder beside that image. An existing backup is never overwritten.

## Supported formats

JPEG/JFIF, PNG, single-frame GIF, BMP/DIB, single-frame TIFF, WebP, TGA, PPM/PGM/PBM/PNM, SGI/RGB, PCX, and AVIF when the installed Pillow build provides an AVIF writer.

Formats that cannot be safely rewritten to the same container/extension are skipped rather than modified.

## Building on Windows

Requirements: Python with pip.

Run:

```bat
build_exe.bat
```

The script installs/updates Pillow and PyInstaller and generates both:

```text
wa_hd_upscale.exe
wa_hd_upscale_silent.exe
```

Temporary PyInstaller files are cleaned automatically. The build script also exits automatically on success; it pauses only when a build error occurs.

The included GitHub Actions workflow can also build both Windows executables manually, on pull requests, or whenever a `v*` tag is pushed. Download the resulting `WhatsApp-HD-image-converter-windows` artifact from the workflow run.

## Running from Python

```text
python wa_hd_upscale.py
```

Examples:

```text
python wa_hd_upscale.py "C:\Photos"
python wa_hd_upscale.py "C:\Photos" --recursive
python wa_hd_upscale.py image1.jpg image2.png
python wa_hd_upscale.py "C:\Photos" --target 3000
python wa_hd_upscale.py "C:\Photos" --quiet
```

## Configuration

Defaults can be changed at the top of `wa_hd_upscale.py`:

| Constant | Default | Purpose |
|---|---:|---|
| `TARGET_LONG_SIDE` | `2560` | Long-side target in pixels |
| `JPEG_QUALITY` | `95` | JPEG/WebP/AVIF quality setting |
| `BACKUP_DIR_NAME` | `wa_originals` | Backup subfolder |
| `SHARPEN_AFTER` | `False` | Optional mild unsharp mask after resizing |
