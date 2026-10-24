# Windows desktop release

AudioVault is a Python/CustomTkinter educational application. Windows downloads are built with **PyInstaller (one-folder mode)** to bundle CustomTkinter themes, fonts, the Python runtime, and supporting libraries.

## Download and launch

1. Open the repository's **Releases** page and select the latest version.
2. Download `AudioVault-Windows-x64.zip` (Windows 10/11, 64-bit).
3. Extract the entire ZIP to a folder you own (for example, `Downloads\AudioVault`).
4. Open the extracted `AudioVault` directory and double-click **`AudioVault.exe`**. Keep the `_internal` folder beside the executable.
5. The program runs without a separate Python installation. Choose your own PNG/JPG/BMP cover and WAV/MP3 or text source.
6. In packaged builds, the application's default output directory is `%USERPROFILE%\AudioVault\output`. Users may select another folder in the save/open dialog.

The executable is **not digitally signed**. Windows SmartScreen or antivirus may display an unknown-publisher warning; verify the download, and run only if you trust the source and your organization's policies permit it. Do not disable antivirus or security protections.

## Verify ZIP integrity (Windows CMD)

From the ZIP download directory:

```cmd
certutil -hashfile AudioVault-Windows-x64.zip SHA256
```

Compare that digest with `AudioVault-Windows-x64.zip.sha256`, which is attached to the same release. The checksum verifies file integrity against the published checksum; it does not establish publisher identity.

## Build locally from source (Windows)

```cmd
cd /d "D:\Desktop\my\dfl\lab project\1st"
venv\Scripts\activate
build_windows.bat
```

This runs the automated test suite before building. Output: `dist\AudioVault\AudioVault.exe` and `AudioVault-Windows-x64.zip`.

## Automated release

The workflow `.github/workflows/windows-release.yml` has two triggers:

- `workflow_dispatch`: run from GitHub Actions to test a Windows build and download the build artifact. **Does not create a Release.**
- Push a version tag `vMAJOR.MINOR.PATCH`, such as `v1.0.0`: builds/tests the Windows distribution, generates a checksum, and creates the GitHub Release with both files attached.

Use a manual workflow run first to validate the `.exe` on a real Windows PC. Then create a version tag.

## Maintenance and caveats

- Keep `.exe` and bundled support files together. Do not upload `AudioVault.exe` by itself.
- This release is **Windows x64 only**. A Mac/Linux build would need to be built on its target OS.
- It is an unsigned educational application, not a formally audited or certified security tool.
- Do not assume that a successful CI unit test guarantees GUI compatibility with every Windows PC; manually test both audio and text hide/extract flows on the extracted build before announcing a stable version.
