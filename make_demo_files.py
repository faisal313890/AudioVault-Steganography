"""Generate safe practice materials (no external assets required)."""
from pathlib import Path
import math
import struct
import wave

from PIL import Image

BASE = Path(__file__).resolve().parent
SAMPLES = BASE / 'samples'
SAMPLES.mkdir(exist_ok=True)

cover = SAMPLES / 'demo_cover.png'
image = Image.new('RGB', (900, 900))
pixels = image.load()
for y in range(900):
    for x in range(900):
        pixels[x, y] = (30 + x * 160 // 900, 45 + y * 110 // 900, 130)
image.save(cover)

sound = SAMPLES / 'demo_voice.wav'
rate = 8000
seconds = 2
with wave.open(str(sound), 'wb') as file:
    file.setnchannels(1)
    file.setsampwidth(2)
    file.setframerate(rate)
    raw = bytearray()
    for t in range(rate * seconds):
        tone = int(11000 * math.sin(2 * math.pi * 440 * t / rate))
        raw.extend(struct.pack('<h', tone))
    file.writeframes(raw)

(SAMPLES / 'secret_message.txt').write_text(
    'Digital Forensics Lab: This is a hidden steganography message.\n'
    'Encrypted using AES-256-GCM and verified by SHA-256.\n',
    encoding='utf-8'
)
print('Demo materials generated successfully:')
for f in [cover, sound, SAMPLES / 'secret_message.txt']:
    print(' -', f)
