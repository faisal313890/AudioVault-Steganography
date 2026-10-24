@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Installing application and build dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m pip install "pyinstaller>=6.10,<7"
if errorlevel 1 exit /b 1

echo [2/4] Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

echo [3/4] Building Windows GUI application...
python -m PyInstaller --noconfirm --clean --onedir --windowed --name AudioVault --collect-all customtkinter main.py
if errorlevel 1 exit /b 1
if not exist "dist\AudioVault\AudioVault.exe" (
    echo ERROR: dist\AudioVault\AudioVault.exe is missing.
    exit /b 1
)

echo [4/4] Compressing distributable folder...
powershell -NoProfile -Command "Compress-Archive -LiteralPath 'dist\AudioVault' -DestinationPath 'AudioVault-Windows-x64.zip' -Force"
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "$h=(Get-FileHash -LiteralPath 'AudioVault-Windows-x64.zip' -Algorithm SHA256).Hash.ToLowerInvariant(); Set-Content -Encoding ASCII -Path 'AudioVault-Windows-x64.zip.sha256' -Value ($h + '  AudioVault-Windows-x64.zip'); Write-Host ('SHA-256: ' + $h)"
if errorlevel 1 exit /b 1

echo.
echo Build completed.
echo To run: dist\AudioVault\AudioVault.exe
echo To distribute: AudioVault-Windows-x64.zip
endlocal
