import math
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image

from steganography import (
    estimate_required_bytes,
    extract_hidden,
    hide_audio,
    hide_text,
    image_capacity,
)


class SteganographyTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.cover = self.root / 'cover.png'
        img = Image.new('RGB', (350, 350), (100, 150, 200))
        img.save(self.cover)
        self.pw = 'StrongTest-Pass123!'

    def test_unicode_text_round_trip_and_hash(self):
        original = 'Digital forensics: خفیہ پیغام 🔐\nline 2\n'
        out = self.root / 'text_stego.png'
        result = hide_text(self.cover, original, out, self.pw)
        self.assertTrue(out.exists())
        self.assertEqual(result['type'], 'text')
        self.assertGreater(result['psnr_db'], 45)
        extract_dir = self.root / 'extracted'
        extracted = extract_hidden(out, self.pw, extract_dir)
        self.assertEqual(extracted['text'], original)
        self.assertTrue(extracted['verified'])
        self.assertEqual((extract_dir/'hidden_message.txt').read_text(encoding='utf8'), original)
        self.assertEqual(result['sha256'], extracted['sha256'])

    def test_wav_round_trip_exact_bytes(self):
        audio = self.root / 'voice.wav'
        with wave.open(str(audio), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b'\x00\x01\xFE\xFF'*2000)
        original = audio.read_bytes()
        out = self.root / 'audio_stego.png'
        result = hide_audio(self.cover, audio, out, self.pw)
        restored = extract_hidden(out, self.pw, self.root / 'recovered')
        self.assertEqual((self.root / 'recovered' / 'voice.wav').read_bytes(), original)
        self.assertEqual(result['sha256'], restored['sha256'])

    def test_mp3_binary_preservation(self):
        audio = self.root / 'voice.mp3'
        audio.write_bytes(b'ID3\x04\x00\x00' + bytes(range(256)) * 10)
        out = self.root / 'stego.png'
        hide_audio(self.cover, audio, out, self.pw)
        recovered = extract_hidden(out, self.pw, self.root / 'rec')
        self.assertEqual(Path(recovered['output']).read_bytes(), audio.read_bytes())

    def test_wrong_password_and_damage(self):
        out = self.root / 'text_stego.png'
        hide_text(self.cover, 'hello', out, self.pw)
        with self.assertRaisesRegex(ValueError, 'password'):
            extract_hidden(out, 'wrong')
        with Image.open(out) as img:
            pixels = bytearray(img.tobytes())
            pixels[350] ^= 1  # flip a bit within encrypted bytes
            damaged = self.root / 'corrupted.png'
            Image.frombytes('RGB', img.size, bytes(pixels)).save(damaged)
        with self.assertRaises(ValueError):
            extract_hidden(damaged, self.pw)

    def test_non_stego_and_capacity(self):
        with self.assertRaisesRegex(ValueError, 'No compatible'):
            extract_hidden(self.cover, self.pw)
        tiny = self.root / 'tiny.png'
        Image.new('RGB', (10, 10), (0,0,0)).save(tiny)
        with self.assertRaisesRegex(ValueError, 'too small'):
            hide_text(tiny, 'x'*100, self.root / 'fail.png', self.pw)

    def test_alpha_channel_preserved(self):
        cover = self.root / 'rgba.png'
        original = Image.new('RGBA', (400, 400), (20, 120, 150, 33))
        original.save(cover)
        out = self.root / 'stego_rgba.png'
        hide_text(cover, 'hello secret', out, self.pw)
        with Image.open(out) as img:
            self.assertEqual(img.mode, 'RGBA')
            self.assertEqual(img.getpixel((0,0))[3], 33)
            self.assertEqual(img.getpixel((350, 350))[3], 33)
        self.assertEqual(extract_hidden(out, self.pw)['text'], 'hello secret')

    def test_no_overwrite(self):
        out = self.root / 'same.png'
        hide_text(self.cover, 'hello', out, self.pw)
        with self.assertRaises(FileExistsError):
            hide_text(self.cover, 'other text', out, self.pw)
        self.assertEqual(extract_hidden(out, self.pw)['text'], 'hello')
        folder = self.root / 'recovered'
        extract_hidden(out, self.pw, folder)
        with self.assertRaises(FileExistsError):
            extract_hidden(out, self.pw, folder)

    def test_capacity_estimate_exact(self):
        cover_cap = image_capacity(self.cover)
        text = 'abc'
        expected = estimate_required_bytes(len(text.encode()), 'hidden_message.txt', 'text')
        result = hide_text(self.cover, text, self.root / 'txt.png', self.pw)
        self.assertEqual(expected, result['used'])
        self.assertEqual(cover_cap, result['capacity'])

if __name__ == '__main__':
    unittest.main()

class AdditionalFormatTests(unittest.TestCase):
    def test_jpeg_cover_converts_to_png(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            cover = folder/'photo.jpg'
            Image.new('RGB', (330, 330), (30, 80, 150)).save(cover, quality=95)
            stego = folder/'hidden.png'
            hide_text(cover, 'JPEG source works', stego, 'A-long-password-1!')
            with Image.open(stego) as im:
                self.assertEqual(im.format, 'PNG')
            self.assertEqual(extract_hidden(stego, 'A-long-password-1!')['text'], 'JPEG source works')

    def test_unauthorized_overwrite_of_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            cover = folder/'cover.png'
            Image.new('RGB', (300, 300), (1, 2, 3)).save(cover)
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                hide_text(cover, 'x', cover, 'abc')
