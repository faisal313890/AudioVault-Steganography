# AudioVault — Digital Forensics GUI Lab Project

Standalone Python application to hide **WAV/MP3 audio** or **UTF-8 text** inside a lossless PNG image, and recover the exact contents.

## Windows CMD quick start

Work in the folder that contains `main.py` (for example `D:\Desktop\my\dfl\lab project\1st`).

```cmd
venv\Scripts\activate
pip install -r requirements.txt
python make_demo_files.py
python -m unittest discover -s tests -v
python main.py
```

If no virtual environment exists, run `python -m venv venv` before activating.

## Using the GUI

**Hide Audio**: choose cover image (PNG/BMP/JPEG), WAV or MP3 file, password. The fixed button at the bottom says **Encrypt & Hide Audio**. Save a *new* `.png` image.

**Hide Text**: choose cover image, type a secret message or use **Import .txt**, and set a password. The fixed bottom button changes to **Encrypt & Hide Text**. Save a *new* `.png` image.

**Extract**: choose the generated PNG, enter the exact password, and choose an output folder. The fixed button says **Extract & Verify Hidden Data**. Audio is restored as WAV/MP3; text is saved as `hidden_message.txt` and displayed in the app. SHA-256 is checked before files are saved.

**Important**: select a fresh output filename and a folder that does not already contain an extracted file of the same name. No source or existing output is overwritten.

## Details for your viva

1. **Steganography vs encryption** — LSB embedding conceals data within the cover image, while AES-256-GCM protects content confidentiality/integrity. Encryption alone does not hide that data exists.
2. **LSB** — replace only the least-significant bit in each R/G/B channel of the image pixel data. The image's alpha channel is not modified.
3. **Capacity** — an RGB image with width W and height H can hold `floor(3*W*H/8)` bytes of raw embedded bits, minus header and encryption overhead.
4. **Scrypt** — derives the AES key from the entered password with a random 16-byte salt. Salt is stored openly in the payload.
5. **AES-256-GCM** — protects the encrypted data using a random 12-byte nonce and a 16-byte authentication tag. Incorrect passwords or corrupted payloads are rejected.
6. **SHA-256** — the plaintext audio/text SHA-256 is computed and stored *inside the encrypted payload*. The extracted content is checked against it.
7. **PNG** — output must stay PNG. Re-saving, resizing, cropping or compressing as JPEG can destroy hidden LSBs.
8. **PSNR** — Peak Signal-to-Noise Ratio measures pixel differences between the converted cover image and the stego image; higher usually indicates less visible distortion. Calculated for RGB channels during embedding.
9. **Digital forensic handling** — use authorized test images/files. Keep originals and working copies separate and document the hashes/paths.

## Implementation notes

- The entire metadata (including the filename), audio or text content and SHA-256 are encrypted. A public image header contains a magic version and encrypted payload length.
- Input audio files are treated as bytes: WAV and MP3 are not transcoded.
- **This format is AudioVault v2** and is not byte-compatible with `AVLT01` images from the earlier tutorial. Regenerate older image outputs using the new app.
- The tool provides **basic sequential spatial LSB steganography**. This is not designed to defeat modern steganalysis. The password may be susceptible to offline guessing if weak; use a long unique password.
- For simplicity, image embedding and extraction operate in memory. Very large audio or cover images may require significant RAM.
- All generated demos are synthetic and safe. `demo_voice.wav` is a computer-generated tone, not human speech.

## Project contents

- `main.py`: CustomTkinter desktop GUI with always-visible action button
- `steganography.py`: LSB image transport, file/text packing and verification
- `security.py`: Scrypt, AES-256-GCM, SHA-256
- `make_demo_files.py`: create a cover PNG, test WAV tone, and text document
- `tests/test_steganography.py`: automated core functionality regression tests
- `requirements.txt`: Python dependencies

Suggested screenshots for your lab report: three main tabs, selected cover + capacity, successful hide result, successful text extraction, successfully restored audio with SHA-256, wrong-password rejection, and test run output.
