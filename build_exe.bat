@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=python"
)

echo Installing/updating required packages...
%PY% -m pip install --upgrade pillow pyinstaller --quiet
if errorlevel 1 goto :error_pip

echo.
echo Building console executable...
%PY% -m PyInstaller --noconfirm --clean --onefile --console --name wa_hd_upscale wa_hd_upscale.py
if errorlevel 1 goto :error_build

echo Building no-window executable...
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --name wa_hd_upscale_silent wa_hd_upscale.py
if errorlevel 1 goto :error_build

copy /Y "dist\wa_hd_upscale.exe" "wa_hd_upscale.exe" >nul
copy /Y "dist\wa_hd_upscale_silent.exe" "wa_hd_upscale_silent.exe" >nul

echo.
echo Built successfully:
echo   wa_hd_upscale.exe         - console output, auto-exits when done
echo   wa_hd_upscale_silent.exe  - no console/window, writes wa_hd_upscale.log

rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul
del /Q wa_hd_upscale.spec 2>nul
del /Q wa_hd_upscale_silent.spec 2>nul
exit /b 0

:error_pip
echo.
echo ERROR: pip failed. Make sure Python is installed and available in PATH.
pause
exit /b 1

:error_build
echo.
echo ERROR: PyInstaller build failed.
pause
exit /b 1
