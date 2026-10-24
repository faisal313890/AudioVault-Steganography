"""Hide encrypted audio or UTF-8 text in PNG using sequential RGB-channel LSBs.

Cover images can be PNG, BMP, or JPEG. Output is always lossless PNG.
This is educational spatial-domain steganography, not a guarantee of
undetectability. Do not recompress or resize a resulting stego PNG.
"""
from __future__ import annotations

import json
import math
import os
import struct
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from security import ENCRYPTION_OVERHEAD, decrypt_data, encrypt_data, sha256_hash

MAGIC = b"AVLT02"
HEADER_SIZE = len(MAGIC) + 8  # version marker + uint64 ciphertext length
INNER_MAGIC = b"AVDATA02"
MAX_METADATA_BYTES = 16_384
AUDIO_EXTENSIONS = {".wav", ".mp3"}
COVER_EXTENSIONS = {".png", ".bmp", ".jpg", ".jpeg"}


def _open_cover(path: str | Path) -> Image.Image:
    path = Path(path)
    if path.suffix.lower() not in COVER_EXTENSIONS:
        raise ValueError("Cover image must be PNG, BMP, JPG or JPEG.")
    try:
        with Image.open(path) as original:
            # Preserve transparency from RGBA and palette PNGs. Change RGB only.
            has_alpha = ("A" in original.getbands() or
                         "transparency" in original.info)
            return original.convert("RGBA" if has_alpha else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The selected cover image could not be read.") from exc


def image_capacity(image_path: str | Path) -> int:
    """Max encrypted packet bytes, excluding the public transport header."""
    image = _open_cover(image_path)
    return max(0, (image.width * image.height * 3) // 8 - HEADER_SIZE)


def estimate_required_bytes(raw_data_size: int, filename: str = "voice.wav", kind: str = "audio") -> int:
    """Estimated encrypted payload size, in bytes (includes AES-GCM overhead)."""
    if raw_data_size < 0:
        raise ValueError("File size cannot be negative.")
    example = {"type": kind, "name": filename, "sha256": "0" * 64}
    metadata_size = len(json.dumps(example, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return len(INNER_MAGIC) + 4 + metadata_size + raw_data_size + ENCRYPTION_OVERHEAD


def _build_plaintext(kind: str, name: str, content: bytes) -> bytes:
    meta = {"type": kind, "name": name, "sha256": sha256_hash(content)}
    metadata = json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(metadata) > MAX_METADATA_BYTES:
        raise ValueError("Embedded metadata is too large.")
    return INNER_MAGIC + struct.pack(">I", len(metadata)) + metadata + content


def _embed(cover: str | Path, packet: bytes, output: str | Path) -> dict:
    cover = Path(cover)
    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError("Stego-image must be saved with a .png extension.")
    if cover.resolve() == output.resolve():
        raise ValueError("The output cannot overwrite the original cover image.")
    if output.exists():
        raise FileExistsError("That output file already exists. Choose a new filename.")

    image = _open_cover(cover)
    width, height = image.size
    channels = len(image.getbands())  # 3 for RGB; 4 for RGBA
    capacity_bits = width * height * 3
    bits_needed = len(packet) * 8
    if bits_needed > capacity_bits:
        available = max(0, capacity_bits // 8 - HEADER_SIZE)
        required = max(0, len(packet) - HEADER_SIZE)
        raise ValueError(
            f"Cover image is too small. Capacity: {available:,} bytes; "
            f"required: {required:,} bytes. Use a larger image or smaller audio/text."
        )

    pixels = bytearray(image.tobytes())
    bit_index = 0
    changed = 0
    for byte in packet:
        for shift in range(7, -1, -1):
            # Ignore every alpha byte when working with an RGBA image.
            channel_index = (bit_index // 3) * channels + bit_index % 3
            original_value = pixels[channel_index]
            new_value = (original_value & 0xFE) | ((byte >> shift) & 1)
            pixels[channel_index] = new_value
            changed += (new_value != original_value)
            bit_index += 1

    stego_image = Image.frombytes(image.mode, image.size, bytes(pixels))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents accidental overwrite. Remove incomplete outputs.
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            stego_image.save(handle, format="PNG")
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise

    mse = changed / (width * height * 3)
    psnr = math.inf if mse == 0 else 10.0 * math.log10(255.0**2 / mse)
    return {
        "output": str(output),
        "capacity": capacity_bits // 8 - HEADER_SIZE,
        "used": len(packet) - HEADER_SIZE,
        "changed_channels": changed,
        "psnr_db": psnr,
        "dimensions": (width, height),
    }


def _hide(cover: str | Path, content: bytes, kind: str, name: str,
          output: str | Path, password: str) -> dict:
    if not password:
        raise ValueError("An encryption password is required.")
    if not content:
        raise ValueError("The content cannot be empty.")
    inner = _build_plaintext(kind, name, content)
    encrypted = encrypt_data(inner, password)
    packet = MAGIC + struct.pack(">Q", len(encrypted)) + encrypted
    info = _embed(cover, packet, output)
    info.update({"type": kind, "name": name, "content_size": len(content),
                 "sha256": sha256_hash(content)})
    return info


def hide_audio(image_path: str | Path, audio_path: str | Path,
               output_path: str | Path, password: str) -> dict:
    audio_path = Path(audio_path)
    if audio_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Audio file must be WAV or MP3.")
    if not audio_path.is_file():
        raise FileNotFoundError("Audio file could not be found.")
    if audio_path.resolve() == Path(output_path).resolve():
        raise ValueError("Output cannot overwrite the original audio.")
    return _hide(image_path, audio_path.read_bytes(), "audio", audio_path.name,
                 output_path, password)


def hide_text(image_path: str | Path, text: str,
              output_path: str | Path, password: str) -> dict:
    if not text.strip():
        raise ValueError("Enter some text before hiding it.")
    return _hide(image_path, text.encode("utf-8"), "text", "hidden_message.txt",
                 output_path, password)


def _read_lsb(pixels: bytes, channels: int, byte_count: int, start_byte: int = 0) -> bytes:
    start_bit = start_byte * 8
    available_bits = (len(pixels) // channels) * 3
    if (start_bit + byte_count * 8) > available_bits:
        raise ValueError("The image does not contain a complete AudioVault payload.")
    result = bytearray(byte_count)
    bit_index = start_bit
    for byte_index in range(byte_count):
        value = 0
        for _ in range(8):
            channel_index = (bit_index // 3) * channels + bit_index % 3
            value = (value << 1) | (pixels[channel_index] & 1)
            bit_index += 1
        result[byte_index] = value
    return bytes(result)


def _read_packet(path: str | Path) -> bytes:
    path = Path(path)
    if path.suffix.lower() != ".png":
        raise ValueError("Choose a lossless .png stego-image.")
    try:
        with Image.open(path) as img:
            if img.format != "PNG":
                raise ValueError("The stego-image must actually be PNG format.")
            image = img.convert("RGBA" if "A" in img.getbands() or "transparency" in img.info else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Could not open the stego-image.") from exc
    pixels = image.tobytes()
    channels = len(image.getbands())
    header = _read_lsb(pixels, channels, HEADER_SIZE)
    if not header.startswith(MAGIC):
        raise ValueError("No compatible AudioVault data found in this image.")
    length = struct.unpack(">Q", header[len(MAGIC):])[0]
    capacity = (image.width * image.height * 3) // 8 - HEADER_SIZE
    if not ENCRYPTION_OVERHEAD <= length <= capacity:
        raise ValueError("The hidden data length is invalid or the image is damaged.")
    return _read_lsb(pixels, channels, length, HEADER_SIZE)


def extract_hidden(image_path: str | Path, password: str,
                   output_directory: str | Path | None = None) -> dict:
    """Automatically recognize hidden text vs audio and verify SHA-256.

    Text is returned in the 'text' field. Audio is written to output_directory
    using exclusive creation, and its destination returned in 'output'.
    """
    decrypted = decrypt_data(_read_packet(image_path), password)
    if not decrypted.startswith(INNER_MAGIC):
        raise ValueError("Decrypted data has an unsupported format.")
    prefix_len = len(INNER_MAGIC)
    if len(decrypted) < prefix_len + 4:
        raise ValueError("Embedded metadata is incomplete.")
    meta_len = struct.unpack(">I", decrypted[prefix_len:prefix_len + 4])[0]
    if meta_len == 0 or meta_len > MAX_METADATA_BYTES:
        raise ValueError("Embedded metadata is invalid.")
    end_meta = prefix_len + 4 + meta_len
    if end_meta > len(decrypted):
        raise ValueError("Embedded metadata is truncated.")
    try:
        meta = json.loads(decrypted[prefix_len + 4:end_meta].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Could not decode embedded metadata.") from exc
    content = decrypted[end_meta:]
    if sha256_hash(content) != meta.get("sha256"):
        raise ValueError("SHA-256 verification failed: content differs.")
    kind = meta.get("type")
    info = {"type": kind, "sha256": sha256_hash(content), "verified": True,
            "content_size": len(content), "name": meta.get("name", "")}
    if kind == "text":
        try:
            info["text"] = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Hidden text is not valid UTF-8.") from exc
        if output_directory is not None:
            out_folder = Path(output_directory)
            out_folder.mkdir(parents=True, exist_ok=True)
            destination = out_folder / "hidden_message.txt"
            with destination.open("xb") as handle:
                handle.write(content)
            info["output"] = str(destination)
        return info
    if kind != "audio":
        raise ValueError("Unsupported embedded content type.")
    if output_directory is None:
        raise ValueError("Choose an output folder to save the recovered audio.")
    name = meta.get("name")
    if not isinstance(name, str) or not name or Path(name).name != name or "\\" in name or Path(name).suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Invalid filename in recovered audio metadata.")
    output_folder = Path(output_directory)
    output_folder.mkdir(parents=True, exist_ok=True)
    destination = output_folder / name
    if destination.resolve() == Path(image_path).resolve():
        raise ValueError("Output cannot overwrite the stego-image.")
    with destination.open("xb") as handle:
        handle.write(content)
    info["output"] = str(destination)
    return info
