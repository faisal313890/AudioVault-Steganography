"""AudioVault GUI - audio AND text steganography in PNG images."""
from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from steganography import (
    estimate_required_bytes, extract_hidden, hide_audio, hide_text, image_capacity
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AudioVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AudioVault | Audio & Text Image Steganography")
        self.geometry("980x760")
        self.minsize(800, 650)
        self.configure(fg_color="#0b1220")

        self.audio_cover = tk.StringVar()
        self.audio_source = tk.StringVar()
        self.text_cover = tk.StringVar()
        self.extract_source = tk.StringVar()
        self.audio_pw = tk.StringVar()
        self.text_pw = tk.StringVar()
        self.extract_pw = tk.StringVar()
        self._result_queue = queue.Queue()
        self._busy = False
        self._last_text = ""
        self._images = {}

        self._build()
        self.after(100, self._poll_results)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(17, 8))
        ctk.CTkLabel(top, text="AUDIOVAULT", font=ctk.CTkFont(size=29, weight="bold"),
                     text_color="#e2e8f0").pack(anchor="w")
        ctk.CTkLabel(top, text="A Digital Forensics Lab Tool  •  LSB Steganography  •  AES-256-GCM  •  SHA-256",
                     font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w")

        self.tabs = ctk.CTkTabview(self, command=self._tab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))
        self.audio_tab = self.tabs.add("Hide Audio")
        self.text_tab = self.tabs.add("Hide Text")
        self.extract_tab = self.tabs.add("Extract")

        self._build_audio()
        self._build_text()
        self._build_extract()

        # One fixed, prominent action button: it cannot scroll out of view.
        bottom = ctk.CTkFrame(self, corner_radius=12, fg_color="#172337")
        bottom.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)
        self.action = ctk.CTkButton(
            bottom, text="Encrypt & Hide Audio", height=46,
            font=ctk.CTkFont(size=16, weight="bold"), command=self._submit,
            fg_color="#2563eb", hover_color="#1d4ed8"
        )
        self.action.grid(row=0, column=0, sticky="ew", padx=14, pady=(13, 8))
        self.progress = ctk.CTkProgressBar(bottom, height=6)
        self.progress.grid(row=1, column=0, sticky="ew", padx=15, pady=4)
        self.progress.set(0)
        self.status = ctk.CTkLabel(bottom, text="Ready — select your files to begin.",
                                   anchor="w", text_color="#cbd5e1")
        self.status.grid(row=2, column=0, sticky="ew", padx=15, pady=(2, 11))

    def _heading(self, parent, title, description):
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=20, weight="bold"),
                     anchor="w").pack(fill="x", pady=(3, 4))
        ctk.CTkLabel(parent, text=description, text_color="#94a3b8",
                     anchor="w", wraplength=730, justify="left").pack(fill="x", pady=(0, 12))

    def _file_row(self, parent, title, variable, browse_label, callback):
        ctk.CTkLabel(parent, text=title, anchor="w", font=ctk.CTkFont(weight="bold"))\
            .pack(fill="x", pady=(8, 3))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))
        ctk.CTkEntry(row, textvariable=variable, state="readonly", height=36)\
            .pack(side="left", fill="x", expand=True, padx=(0, 9))
        ctk.CTkButton(row, text=browse_label, width=122, height=36,
                      command=callback).pack(side="left")

    def _password(self, parent, variable):
        ctk.CTkLabel(parent, text="Encryption / decryption password", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(10, 3))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        entry = ctk.CTkEntry(row, textvariable=variable, show="*", height=36,
                             placeholder_text="Enter password (do not lose it)")
        entry.pack(side="left", fill="x", expand=True)
        show = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(row, text="Show", variable=show, width=75,
                        command=lambda: entry.configure(show="" if show.get() else "*"))\
            .pack(side="left", padx=(12, 0))

    def _preview(self, parent, name):
        frame = ctk.CTkFrame(parent, fg_color="#19263a", height=125)
        frame.pack(fill="x", pady=(13, 6))
        frame.pack_propagate(False)
        label = ctk.CTkLabel(frame, text="Cover image preview will appear here",
                             text_color="#94a3b8")
        label.pack(expand=True)
        setattr(self, name, label)

    def _build_audio(self):
        panel = ctk.CTkScrollableFrame(self.audio_tab, fg_color="transparent")
        panel.pack(fill="both", expand=True, padx=15, pady=8)
        self._heading(panel, "Hide a WAV or MP3 file",
                      "Choose a cover image and an audio file. The encrypted audio is embedded into a new PNG image.")
        self._file_row(panel, "Cover image (PNG / JPG / BMP)", self.audio_cover,
                       "Select Image", lambda: self._choose_cover("audio"))
        self._file_row(panel, "Secret audio (WAV / MP3)", self.audio_source,
                       "Select Audio", self._choose_audio)
        self._password(panel, self.audio_pw)
        self.audio_capacity = ctk.CTkLabel(panel, text="Capacity: select a cover image",
                                           anchor="w", text_color="#94a3b8")
        self.audio_capacity.pack(fill="x", pady=(12, 0))
        self._preview(panel, "audio_preview")
        ctk.CTkLabel(panel, text="Output is lossless PNG. Do not convert it to JPEG afterward.",
                     text_color="#94a3b8", anchor="w").pack(fill="x", pady=(5, 4))

    def _build_text(self):
        panel = ctk.CTkScrollableFrame(self.text_tab, fg_color="transparent")
        panel.pack(fill="both", expand=True, padx=15, pady=8)
        self._heading(panel, "Hide a secret text message",
                      "Type a message or import a UTF-8 .txt file, then encrypt and hide it in an image.")
        self._file_row(panel, "Cover image (PNG / JPG / BMP)", self.text_cover,
                       "Select Image", lambda: self._choose_cover("text"))
        ctk.CTkLabel(panel, text="Secret message", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(9, 3))
        self.text_box = ctk.CTkTextbox(panel, height=112, wrap="word")
        self.text_box.pack(fill="x")
        text_buttons = ctk.CTkFrame(panel, fg_color="transparent")
        text_buttons.pack(fill="x", pady=(5, 0))
        ctk.CTkButton(text_buttons, text="Import .txt", width=112,
                      command=self._import_text).pack(side="left")
        ctk.CTkButton(text_buttons, text="Clear", width=78, fg_color="#475569",
                      command=lambda: self.text_box.delete("1.0", "end"))\
            .pack(side="left", padx=(9, 0))
        self._password(panel, self.text_pw)
        self.text_capacity = ctk.CTkLabel(panel, text="Capacity: select a cover image",
                                          anchor="w", text_color="#94a3b8")
        self.text_capacity.pack(fill="x", pady=(10, 0))
        self.text_box.bind("<KeyRelease>", lambda _event: self._update_capacity("text"))
        self._preview(panel, "text_preview")

    def _build_extract(self):
        panel = ctk.CTkScrollableFrame(self.extract_tab, fg_color="transparent")
        panel.pack(fill="both", expand=True, padx=15, pady=8)
        self._heading(panel, "Extract hidden audio or text",
                      "No need to select the type. AudioVault automatically identifies the encrypted content after decryption.")
        self._file_row(panel, "Stego-image (PNG)", self.extract_source,
                       "Select Image", self._choose_stego)
        self._password(panel, self.extract_pw)
        ctk.CTkLabel(panel, text="Recovered text / verification result", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(18, 6))
        self.extracted_box = ctk.CTkTextbox(panel, height=180, wrap="word")
        self.extracted_box.pack(fill="both", expand=True)
        self.extracted_box.configure(state="disabled")
        self.copy_button = ctk.CTkButton(panel, text="Copy Recovered Text",
                                         state="disabled", command=self._copy_text)
        self.copy_button.pack(anchor="w", pady=(8, 6))

    def _tab_changed(self):
        labels = {"Hide Audio": "Encrypt & Hide Audio",
                  "Hide Text": "Encrypt & Hide Text",
                  "Extract": "Extract & Verify Hidden Data"}
        self.action.configure(text=labels.get(self.tabs.get(), "Run Operation"))

    def _choose_cover(self, mode):
        path = filedialog.askopenfilename(title="Select a cover image",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        try:
            capacity = image_capacity(path)
            with Image.open(path) as img:
                preview = img.copy()
                preview.thumbnail((280, 112))
            cimg = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Invalid Image", str(exc))
            return
        if mode == "audio":
            self.audio_cover.set(path)
            label = self.audio_preview
        else:
            self.text_cover.set(path)
            label = self.text_preview
        self._images[mode] = cimg  # Retain image reference
        label.configure(image=cimg, text="")
        self._update_capacity(mode)
        self._set_status(f"Cover image loaded — capacity {capacity:,} bytes.")

    def _choose_audio(self):
        path = filedialog.askopenfilename(title="Select audio", filetypes=[("Audio", "*.wav *.mp3")])
        if path:
            self.audio_source.set(path)
            self._update_capacity("audio")

    def _choose_stego(self):
        path = filedialog.askopenfilename(title="Select a stego PNG", filetypes=[("PNG", "*.png")])
        if path:
            self.extract_source.set(path)

    def _import_text(self):
        path = filedialog.askopenfilename(title="Import UTF-8 text", filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Could not read text", str(exc))
            return
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)
        self._update_capacity("text")

    def _update_capacity(self, mode):
        try:
            if mode == "audio":
                cover = self.audio_cover.get()
                audio = self.audio_source.get()
                label = self.audio_capacity
                if not cover:
                    return
                cap = image_capacity(cover)
                if not audio or not Path(audio).is_file():
                    label.configure(text=f"Available capacity: {cap:,} bytes. Select audio to estimate usage.",
                                    text_color="#94a3b8")
                    return
                required = estimate_required_bytes(Path(audio).stat().st_size, Path(audio).name, "audio")
            else:
                cover = self.text_cover.get()
                label = self.text_capacity
                if not cover:
                    return
                cap = image_capacity(cover)
                size = len(self.text_box.get("1.0", "end-1c").encode("utf-8"))
                required = estimate_required_bytes(size, "hidden_message.txt", "text")
            fits = required <= cap
            label.configure(
                text=f"Capacity: {cap:,} bytes  |  Estimated required: {required:,} bytes  |  {'Fits ✓' if fits else 'Too large ✗'}",
                text_color="#4ade80" if fits else "#f87171"
            )
        except (OSError, ValueError) as exc:
            label.configure(text=f"Cannot estimate capacity: {exc}", text_color="#f87171")

    def _set_status(self, value):
        self.status.configure(text=value)

    def _set_busy(self, busy, status):
        self._busy = busy
        self.action.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(1 if status.startswith("Success") else 0)
        self._set_status(status)

    def _submit(self):
        if self._busy:
            return
        mode = self.tabs.get()
        if mode == "Hide Audio":
            cover, audio, pw = self.audio_cover.get(), self.audio_source.get(), self.audio_pw.get()
            if not cover or not audio or not pw:
                messagebox.showwarning("Required fields", "Choose an image, an audio file and a password.")
                return
            output = filedialog.asksaveasfilename(title="Save stego-image", initialdir=str(OUTPUT_DIR),
                                                  initialfile="hidden_audio.png", defaultextension=".png",
                                                  filetypes=[("PNG", "*.png")])
            if not output:
                return
            operation = lambda: hide_audio(cover, audio, output, pw)
        elif mode == "Hide Text":
            cover, text, pw = self.text_cover.get(), self.text_box.get("1.0", "end-1c"), self.text_pw.get()
            if not cover or not text.strip() or not pw:
                messagebox.showwarning("Required fields", "Choose an image, enter text and a password.")
                return
            output = filedialog.asksaveasfilename(title="Save stego-image", initialdir=str(OUTPUT_DIR),
                                                  initialfile="hidden_text.png", defaultextension=".png",
                                                  filetypes=[("PNG", "*.png")])
            if not output:
                return
            operation = lambda: hide_text(cover, text, output, pw)
        else:
            stego, pw = self.extract_source.get(), self.extract_pw.get()
            if not stego or not pw:
                messagebox.showwarning("Required fields", "Choose a stego PNG and enter the password.")
                return
            folder = filedialog.askdirectory(title="Select folder to save extracted data",
                                             initialdir=str(OUTPUT_DIR))
            if not folder:
                return
            operation = lambda: extract_hidden(stego, pw, folder)
        self._set_busy(True, "Processing securely... (the GUI will remain responsive)")
        threading.Thread(target=self._worker, args=(operation,), daemon=True).start()

    def _worker(self, operation):
        try:
            self._result_queue.put(("success", operation()))
        except Exception as exc:
            self._result_queue.put(("error", str(exc)))

    def _poll_results(self):
        try:
            while True:
                status, data = self._result_queue.get_nowait()
                if status == "success":
                    self._success(data)
                else:
                    self._set_busy(False, "Error — check the message and retry.")
                    messagebox.showerror("AudioVault Error", data)
        except queue.Empty:
            pass
        self.after(100, self._poll_results)

    def _success(self, result):
        self._set_busy(False, "Success — operation completed and verified.")
        kind = result["type"]
        lines = [f"Type: {kind.upper()}", f"SHA-256: {result['sha256']}"]
        if "output" in result:
            lines.insert(0, f"Saved: {result['output']}")
        if "psnr_db" in result:
            psnr = result["psnr_db"]
            lines.append(f"PSNR vs cover: {psnr:.2f} dB" if math.isfinite(psnr) else "PSNR: unchanged")
            lines.append(f"Image payload used: {result['used']:,} / {result['capacity']:,} bytes")
        if result.get("verified"):
            lines.append("Integrity: SHA-256 VERIFIED ✓")
        if kind == "text" and "text" in result:
            self._last_text = result["text"]
            self.extracted_box.configure(state="normal")
            self.extracted_box.delete("1.0", "end")
            self.extracted_box.insert("1.0", self._last_text)
            self.extracted_box.configure(state="disabled")
            self.copy_button.configure(state="normal")
        messagebox.showinfo("AudioVault Success", "\n".join(lines))

    def _copy_text(self):
        if self._last_text:
            self.clipboard_clear()
            self.clipboard_append(self._last_text)
            self._set_status("Recovered text copied to clipboard.")


if __name__ == "__main__":
    AudioVaultApp().mainloop()
