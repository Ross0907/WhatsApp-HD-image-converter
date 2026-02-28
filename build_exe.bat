@echo off
echo Installing/updating required packages...
pip install pillow pyinstaller --upgrade --quiet
if errorlevel 1 (
    echo ERROR: pip failed. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)

echo.
echo Building single-file executable...
python -m PyInstaller --onefile --console --name wa_hd_upscale wa_hd_upscale.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

:: Move exe to current folder for convenience
if exist dist\wa_hd_upscale.exe (
    copy /Y dist\wa_hd_upscale.exe wa_hd_upscale.exe
    echo.
    echo  wa_hd_upscale.exe was generated successfully
    echo  Copy it next to any batch of images and execute it to upscale to WA HD threshold.
) else (
    echo Could not find built exe.
)

:: Clean up PyInstaller temp files
rmdir /S /Q build 2>nul
rmdir /S /Q dist  2>nul
del /Q wa_hd_upscale.spec 2>nul

pause
