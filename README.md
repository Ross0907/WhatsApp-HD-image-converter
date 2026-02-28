# WhatsApp HD Upscaler

WhatsApp only offers HD quality when the long side of an image is above roughly 1600px. Many photos — especially screenshots, compressed images, or anything resized for web — fall below this and get silently compressed further. This tool brings them all up to 2560px on the long side before you send.

Download the prebuilt exe: [here](https://github.com/Ross0907/WhatsApp-HD-image-converter/releases/download/v1/wa_hd_upscale.exe)

## Usage

Drop `wa_hd_upscale.exe` into any folder containing images and double-click it. It will scan the folder, upscale anything below the threshold, and save each file back to its original format and extension. A copy of every original is preserved in a `wa_originals` subfolder before any changes are made.

Images that are already large enough are skipped automatically.


## Supported formats

JPEG, PNG, GIF, BMP, TIFF, WebP, TGA, ICO, PCX, PPM/PGM/PBM, SGI, AVIF, HEIC, HEIF, EXR, HDR, DDS, XBM, and more. Any format readable by Pillow is handled.


## Building from source

**Requirements:** Python 3.8 or later with pip.

1. Clone the repository and open a terminal in the project folder.

2. Install dependencies and build the executable:
   ```
   build_exe.bat
   ```
   This installs Pillow and PyInstaller, compiles a single portable `wa_hd_upscale.exe`, and cleans up build artifacts automatically.

3. The finished `wa_hd_upscale.exe` will appear in the same folder. It has no external dependencies and can be copied anywhere.

If you prefer to run the script directly without building:
```
pip install pillow
python wa_hd_upscale.py
```


## Configuration

The following constants at the top of `wa_hd_upscale.py` can be adjusted before building:

| Constant | Default | Description |
|---|---|---|
| `TARGET_LONG_SIDE` | `2560` | Target resolution in pixels for the long side |
| `JPEG_QUALITY` | `95` | JPEG save quality (1–95) |
| `BACKUP_DIR_NAME` | `wa_originals` | Name of the backup subfolder |


## Notes

- PSD files cannot be written by Pillow; they are saved as TIFF using the same filename.
- Animated GIFs are processed on the first frame only.
- The tool will never shrink an image that is already above the target resolution.
