# Architecture and security design

## Scope

AudioVault is a local desktop steganography demonstration. It embeds **encrypted payload bytes** into the least significant bits of RGB color channels in a new **lossless PNG** image. Inputs may be a WAV/MP3 file or UTF-8 text. The image itself is not encrypted; the hidden payload is encrypted.

## Components

| File | Responsibility |
|---|---|
| `main.py` | Desktop workflow, file dialogs, text entry, capacity feedback, operation status and results |
| `steganography.py` | Prepare metadata, package content, capacity checks, LSB embedding/extraction, PSNR, output safety |
| `security.py` | Scrypt password-to-key derivation; AES-256-GCM; SHA-256 |
| `tests/test_steganography.py` | Automated round trips and failure-path checks |

## Encode flow

1. User selects an image, either a WAV/MP3 file or text, a destination and a password.
2. Validate supported formats, non-empty content, permitted output path and capacity.
3. Build an inner package containing content type, filename, SHA-256 digest, and raw original bytes.
4. Derive an AES-256 encryption key using Scrypt with a random salt; AES-GCM encrypts/authenticates the package with a random nonce.
5. Prepend a public `AVLT02` marker and encrypted-length header; embed the packet sequentially into RGB-channel LSBs.
6. Save a **new PNG** image and report payload size and PSNR.

## Decode flow

1. Read the header and ciphertext from the stego PNG's RGB LSB stream.
2. Validate header and packet length, derive the key from the supplied password, authenticate/decrypt with AES-GCM.
3. Read the decrypted metadata and original data; re-compute SHA-256 and compare to the embedded digest.
4. Identify audio or text automatically; save in a user-selected folder without replacing existing files. For text, also display the recovered message.

## Embedding capacity

For an RGB cover (or the RGB portion of an RGBA image):

```text
max raw bit capacity = image_width × image_height × 3
max raw byte capacity = floor(max raw bit capacity / 8)
usable encrypted packet bytes = raw byte capacity − transport header
```

The application also accounts for metadata and AES-GCM overhead when estimating required bytes. The **8,255-byte** capacity shown in the supplied example is *not* a general fixed limitation; it depends on the selected image's dimensions.

## PSNR

PSNR (peak signal-to-noise ratio) expresses pixel-channel difference between the converted cover and stego image:

```text
MSE = (1 / N) × Σ(cover_channel − stego_channel)²
PSNR = 10 log10(255² / MSE) dB
```

Because one LSB is replaced per channel, each changed RGB value differs by at most one; in this implementation, squared error is one for each changed channel. Larger PSNR indicates lower distortion under this metric, **not** guaranteed concealment.

## Threat model / limitations

**Provides:** password-derived authenticated encryption of the payload; rejection of wrong password/corrupted ciphertext; SHA-256 recovered-content equality check; avoidance of accidental overwrites.

**Does not provide:** guaranteed undetectability, protection against malicious changes to arbitrary image pixel data, resilience to recompression/resizing, secure memory erasure, professional forensic provenance, or a verified defense against sophisticated offline password guessing.

A short demo password (even if masked in screenshots) should **not** be reused for real confidential material. Use a long unique password and avoid committing any sensitive test material, generated stego images or private audio recordings.
