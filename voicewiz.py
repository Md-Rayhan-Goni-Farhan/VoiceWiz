import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os, sys, json, threading, time, shutil, wave
import sounddevice as sd
import soundfile as sf
import numpy as np

# ─────────────────────────────────────────
#  CONSTANTS & PATHS
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR  = os.path.join(BASE_DIR, "profiles")
VOICES_DIR    = os.path.join(BASE_DIR, "voices")
TEMP_DIR      = os.path.join(BASE_DIR, "temp")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")

for d in [PROFILES_DIR, VOICES_DIR, TEMP_DIR, ASSETS_DIR]:
    os.makedirs(d, exist_ok=True)

# ─────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────
BG_DARK   = "#0A0A12"
BG_PANEL  = "#13131F"
BG_CARD   = "#1C1C2E"
ACCENT1   = "#00D4FF"
ACCENT2   = "#9B59FF"
ACCENT3   = "#39FF6E"
ACCENT4   = "#FF6B35"
TEXT_PRI  = "#E8E8F0"
TEXT_SEC  = "#7A7A9A"
BTN_HVR   = "#1A1A2E"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────

def load_profiles():
    profiles = []
    for name in os.listdir(PROFILES_DIR):
        meta_path = os.path.join(PROFILES_DIR, name, "meta.json")
        if os.path.isdir(os.path.join(PROFILES_DIR, name)) and os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meta["folder"] = name
            profiles.append(meta)
    return profiles

def make_circle_image(path, size=80):
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    except Exception:
        img = Image.new("RGBA", (size, size), "#2A2A3E")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

def default_avatar(size=80):
    img = Image.new("RGBA", (size, size), "#2A2A3E")
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, size, size), fill="#3A3A5E")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

# ─────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────

class VoiceWizApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VoiceWiz")
        self.geometry("520x820")
        self.minsize(480, 700)
        self.configure(fg_color=BG_DARK)
        self.resizable(True, True)

        self._recording = False
        self._rec_thread = None
        self._recorded_path = None
        self._rec_frames = []
        self._last_converted = None
        self._selected_file_path = None

        self._build_ui()
        self.show_home()

    def _build_ui(self):
        self.header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=60)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.logo_lbl = ctk.CTkLabel(
            self.header, text="VOICE WIZ",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=ACCENT1)
        self.logo_lbl.pack(side="left", padx=20, pady=10)

        self.page_lbl = ctk.CTkLabel(
            self.header, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_SEC)
        self.page_lbl.pack(side="right", padx=20, pady=10)

        self.content = ctk.CTkScrollableFrame(
            self, fg_color=BG_DARK,
            scrollbar_button_color=BG_PANEL,
            scrollbar_button_hover_color=ACCENT2)
        self.content.pack(fill="both", expand=True)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _set_page(self, name):
        self.page_lbl.configure(text=name)

    def _back_btn(self, cmd=None):
        btn = ctk.CTkButton(
            self.content, text="← Back",
            font=ctk.CTkFont(size=12), height=28, width=90,
            fg_color="transparent", text_color=TEXT_SEC,
            hover_color=BTN_HVR, border_width=1, border_color="#3A3A5A",
            command=cmd or self.show_home)
        btn.pack(anchor="w", padx=20, pady=(14, 4))

    # ─────────────────────────────────────
    #  HOME SCREEN
    # ─────────────────────────────────────
    def show_home(self):
        self._clear_content()
        self._set_page("")

        ctk.CTkLabel(self.content, text="Your local voice style studio",
                     font=ctk.CTkFont(size=13), text_color=TEXT_SEC
                     ).pack(pady=(22, 2))

        actions = [
            ("🎙  Record Your Voice",         ACCENT1,   "#0099BB", self.show_record),
            ("📂  Select a Recorded File",     ACCENT2,   "#7A44CC", self.show_select_file),
            ("🎓  Train a New Character",      "#4A90D9", "#2A60A9", self.show_train),
            ("🧩  Manage Characters",          ACCENT3,   "#28CC55", self.show_manage_characters),
            ("🔊  Manage Created Voices",      ACCENT4,   "#CC4A1A", self.show_manage_voices),
            ("▶   Demo a Character",          "#D4A017", "#AA7800", self.show_demo),
        ]

        for label, fg, hover, cmd in actions:
            btn = ctk.CTkButton(
                self.content, text=label,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                height=58, corner_radius=30,
                fg_color=fg, hover_color=hover,
                text_color="#000000" if fg == ACCENT3 else TEXT_PRI,
                command=cmd)
            btn.pack(fill="x", padx=30, pady=7)

        ctk.CTkLabel(self.content, text="Trained Characters",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_SEC).pack(pady=(22, 6))

        self._render_character_strip()

        disc = (
            "*VoiceWiz is made for creators who cannot afford professional voice actors,\n"
            "or need voices for small-scale personal projects.\n"
            "VoiceWiz does not promote copyright infringement or plagiarism.\n"
            "The developer is not responsible for any violation committed by the user.*"
        )
        ctk.CTkLabel(self.content, text=disc,
                     font=ctk.CTkFont(size=10, slant="italic"),
                     text_color=TEXT_SEC, wraplength=420, justify="center"
                     ).pack(pady=(18, 24))

    def _render_character_strip(self):
        profiles = load_profiles()
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=4)

        if not profiles:
            ctk.CTkLabel(frame,
                         text="No characters added yet.\nUse 'Train a New Character' to get started.",
                         font=ctk.CTkFont(size=12), text_color=TEXT_SEC,
                         justify="center").pack(pady=16)
            return

        cols = 3
        for i, p in enumerate(profiles[:6]):
            col = i % cols
            row = i // cols
            card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=14,
                                 width=130, height=160)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)
            frame.grid_columnconfigure(col, weight=1)

            photo_path = p.get("photo", "")
            img = make_circle_image(photo_path, 72) if (
                photo_path and os.path.exists(photo_path)) else default_avatar(72)

            ctk.CTkLabel(card, text="", image=img).pack(pady=(14, 4))
            ctk.CTkLabel(card, text=p.get("name", "Unknown").upper(),
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=ACCENT1, wraplength=110).pack()

            tags = p.get("tags", [])
            tag_text = "\n".join(f"• {t}" for t in tags[:3]) if tags else ""
            ctk.CTkLabel(card, text=tag_text,
                         font=ctk.CTkFont(size=9), text_color=TEXT_SEC,
                         wraplength=110, justify="left").pack(pady=(2, 8))

    # ─────────────────────────────────────
    #  RECORD VOICE PAGE
    # ─────────────────────────────────────
    def show_record(self):
        self._clear_content()
        self._set_page("Record Your Voice")
        self._back_btn()

        ctk.CTkLabel(self.content, text="🎙 Record Your Voice",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))
        ctk.CTkLabel(self.content,
                     text="Speak naturally. The app will convert your recording\nto sound like the selected character.",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC,
                     justify="center").pack(pady=(0, 20))

        ctk.CTkLabel(self.content, text="Convert to:",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30)
        profiles = load_profiles()
        pnames = [p.get("name", "?") for p in profiles] if profiles else ["No characters yet"]
        self._char_var = ctk.StringVar(value=pnames[0])
        ctk.CTkOptionMenu(self.content, values=pnames, variable=self._char_var,
                          fg_color=BG_CARD, button_color=ACCENT2,
                          font=ctk.CTkFont(size=13), height=38
                          ).pack(fill="x", padx=30, pady=(4, 20))

        self._rec_status = ctk.CTkLabel(self.content, text="Ready to record",
                                         font=ctk.CTkFont(size=13),
                                         text_color=TEXT_SEC)
        self._rec_status.pack(pady=8)

        self._rec_btn = ctk.CTkButton(
            self.content, text="⏺  START RECORDING",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=60, corner_radius=30,
            fg_color="#CC2222", hover_color="#992222",
            command=self._toggle_recording)
        self._rec_btn.pack(fill="x", padx=40, pady=8)

        self._conv_btn = ctk.CTkButton(
            self.content, text="⚡ CONVERT VOICE",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=60, corner_radius=30,
            fg_color=ACCENT2, hover_color="#7A33CC",
            state="disabled", command=self._run_conversion)
        self._conv_btn.pack(fill="x", padx=40, pady=8)

        self._prog_bar = ctk.CTkProgressBar(self.content, height=10,
                                             progress_color=ACCENT1)
        self._prog_bar.set(0)
        self._prog_bar.pack(fill="x", padx=40, pady=(10, 4))
        self._prog_lbl = ctk.CTkLabel(self.content, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color=TEXT_SEC)
        self._prog_lbl.pack()

        play_frame = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=12)
        play_frame.pack(fill="x", padx=30, pady=(18, 8))
        ctk.CTkLabel(play_frame, text="Playback",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT_SEC).pack(pady=(10, 4))
        pb_row = ctk.CTkFrame(play_frame, fg_color="transparent")
        pb_row.pack(pady=(0, 12))
        ctk.CTkButton(pb_row, text="▶ Original", width=130, height=36,
                      fg_color=BG_PANEL, hover_color=BTN_HVR,
                      command=self._play_original).pack(side="left", padx=8)
        ctk.CTkButton(pb_row, text="▶ Converted", width=130, height=36,
                      fg_color=ACCENT1, text_color="#000",
                      hover_color="#0099BB",
                      command=self._play_converted).pack(side="left", padx=8)

    # ─────────────────────────────────────
    #  SELECT FILE PAGE
    # ─────────────────────────────────────
    def show_select_file(self):
        self._clear_content()
        self._set_page("Select a Recorded File")
        self._back_btn()

        ctk.CTkLabel(self.content, text="📂 Use a Pre-Recorded File",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))
        ctk.CTkLabel(self.content,
                     text="Browse for a WAV or MP3 file of your own voice to convert.",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC,
                     justify="center").pack(pady=(0, 20))

        self._file_lbl = ctk.CTkLabel(self.content, text="No file selected",
                                       font=ctk.CTkFont(size=12),
                                       text_color=TEXT_SEC)
        self._file_lbl.pack(pady=8)

        ctk.CTkButton(self.content, text="📁  Browse File",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      height=52, corner_radius=26,
                      fg_color=ACCENT2, hover_color="#7A33CC",
                      command=self._browse_voice_file
                      ).pack(fill="x", padx=40, pady=8)

        ctk.CTkLabel(self.content, text="Convert to:",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30, pady=(16, 2))
        profiles = load_profiles()
        pnames = [p.get("name", "?") for p in profiles] if profiles else ["No characters yet"]
        self._file_char_var = ctk.StringVar(value=pnames[0])
        ctk.CTkOptionMenu(self.content, values=pnames,
                          variable=self._file_char_var,
                          fg_color=BG_CARD, button_color=ACCENT2,
                          font=ctk.CTkFont(size=13), height=38
                          ).pack(fill="x", padx=30, pady=(0, 16))

        self._file_conv_btn = ctk.CTkButton(
            self.content, text="⚡ CONVERT VOICE",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=60, corner_radius=30,
            fg_color=ACCENT1, text_color="#000", hover_color="#0099BB",
            state="disabled", command=self._run_file_conversion)
        self._file_conv_btn.pack(fill="x", padx=40, pady=8)

        self._file_prog_bar = ctk.CTkProgressBar(self.content, height=10,
                                                   progress_color=ACCENT1)
        self._file_prog_bar.set(0)
        self._file_prog_bar.pack(fill="x", padx=40, pady=(10, 4))
        self._file_prog_lbl = ctk.CTkLabel(self.content, text="",
                                             font=ctk.CTkFont(size=11),
                                             text_color=TEXT_SEC)
        self._file_prog_lbl.pack()

    # ─────────────────────────────────────
    #  TRAIN CHARACTER PAGE
    # ─────────────────────────────────────
    def show_train(self):
        self._clear_content()
        self._set_page("Train a New Character")
        self._back_btn()

        ctk.CTkLabel(self.content, text="🎓 Train a New Character",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))
        ctk.CTkLabel(self.content,
                     text="Drop in any audio of the character's voice (1–30 mins).\nVoiceWiz extracts a clean reference — no long training wait.",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC,
                     justify="center").pack(pady=(0, 16))

        ctk.CTkLabel(self.content, text="Character Name:",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30)
        self._train_name = ctk.CTkEntry(
            self.content, placeholder_text="e.g. Eren Yeager",
            height=40, fg_color=BG_CARD, border_color=ACCENT2)
        self._train_name.pack(fill="x", padx=30, pady=(4, 12))

        ctk.CTkLabel(self.content,
                     text="Tags  (comma separated — type, traits, etc.):",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30)
        self._train_tags = ctk.CTkEntry(
            self.content,
            placeholder_text="e.g. Anime type, Mid 20s man, Deep, Serious",
            height=40, fg_color=BG_CARD, border_color=ACCENT2)
        self._train_tags.pack(fill="x", padx=30, pady=(4, 12))

        ctk.CTkLabel(self.content, text="Character Photo  (optional):",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30)
        photo_row = ctk.CTkFrame(self.content, fg_color="transparent")
        photo_row.pack(fill="x", padx=30, pady=(4, 12))
        self._train_photo_lbl = ctk.CTkLabel(
            photo_row, text="No photo selected",
            font=ctk.CTkFont(size=11), text_color=TEXT_SEC)
        self._train_photo_lbl.pack(side="left", expand=True, anchor="w")
        ctk.CTkButton(photo_row, text="Browse", width=90, height=32,
                      fg_color=BG_CARD, hover_color=BTN_HVR,
                      border_width=1, border_color="#3A3A5A",
                      command=self._pick_train_photo).pack(side="right")
        self._train_photo_path = None

        ctk.CTkLabel(self.content, text="Audio Files  (WAV or MP3):",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(anchor="w", padx=30)
        audio_row = ctk.CTkFrame(self.content, fg_color="transparent")
        audio_row.pack(fill="x", padx=30, pady=(4, 4))
        self._audio_count_lbl = ctk.CTkLabel(
            audio_row, text="No files selected",
            font=ctk.CTkFont(size=11), text_color=TEXT_SEC)
        self._audio_count_lbl.pack(side="left", expand=True, anchor="w")
        ctk.CTkButton(audio_row, text="Browse", width=90, height=32,
                      fg_color=BG_CARD, hover_color=BTN_HVR,
                      border_width=1, border_color="#3A3A5A",
                      command=self._pick_audio_files).pack(side="right")
        self._train_audio_files = []

        self._train_btn = ctk.CTkButton(
            self.content, text="🚀  START",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=60, corner_radius=30,
            fg_color=ACCENT3, text_color="#000", hover_color="#28CC55",
            command=self._start_training)
        self._train_btn.pack(fill="x", padx=30, pady=(20, 8))

        self._train_prog = ctk.CTkProgressBar(self.content, height=12,
                                               progress_color=ACCENT3)
        self._train_prog.set(0)
        self._train_prog.pack(fill="x", padx=30, pady=(8, 4))
        self._train_prog_lbl = ctk.CTkLabel(
            self.content, text="",
            font=ctk.CTkFont(size=11), text_color=TEXT_SEC)
        self._train_prog_lbl.pack(pady=(0, 20))

    # ─────────────────────────────────────
    #  MANAGE CHARACTERS PAGE
    # ─────────────────────────────────────
    def show_manage_characters(self):
        self._clear_content()
        self._set_page("Manage Characters")
        self._back_btn()

        ctk.CTkLabel(self.content, text="🧩 Manage Characters",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))

        profiles = load_profiles()
        if not profiles:
            ctk.CTkLabel(self.content,
                         text="No characters added yet.\nGo to 'Train a New Character' to add one.",
                         font=ctk.CTkFont(size=13), text_color=TEXT_SEC,
                         justify="center").pack(pady=40)
            return

        for p in profiles:
            self._render_char_card(p)

    def _render_char_card(self, p):
        card = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=14)
        card.pack(fill="x", padx=24, pady=8)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        photo_path = p.get("photo", "")
        img = make_circle_image(photo_path, 60) if (
            photo_path and os.path.exists(photo_path)) else default_avatar(60)
        ctk.CTkLabel(row, text="", image=img).pack(side="left", padx=(0, 14))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(info, text=p.get("name", "Unknown"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=ACCENT1, anchor="w").pack(anchor="w")
        tags = ", ".join(p.get("tags", []))
        ctk.CTkLabel(info, text=tags or "No tags",
                     font=ctk.CTkFont(size=11), text_color=TEXT_SEC,
                     anchor="w", wraplength=220).pack(anchor="w")

        ctk.CTkButton(row, text="🗑 Delete", width=80, height=30,
                      fg_color="#441111", hover_color="#882222",
                      font=ctk.CTkFont(size=11),
                      command=lambda pf=p: self._delete_profile(pf)
                      ).pack(side="right")

    # ─────────────────────────────────────
    #  MANAGE VOICES PAGE
    # ─────────────────────────────────────
    def show_manage_voices(self):
        self._clear_content()
        self._set_page("Manage Voices")
        self._back_btn()

        ctk.CTkLabel(self.content, text="🔊 Your Converted Voices",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))

        wavs = [f for f in os.listdir(VOICES_DIR) if f.endswith(".wav")]
        if not wavs:
            ctk.CTkLabel(self.content,
                         text="No converted voices yet.\nRecord and convert to create one.",
                         font=ctk.CTkFont(size=13), text_color=TEXT_SEC,
                         justify="center").pack(pady=40)
            return

        for fname in sorted(wavs, reverse=True):
            fpath = os.path.join(VOICES_DIR, fname)
            card = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=12)
            card.pack(fill="x", padx=24, pady=6)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=10)
            ctk.CTkLabel(row, text=fname, font=ctk.CTkFont(size=12),
                         text_color=TEXT_PRI, anchor="w"
                         ).pack(side="left", expand=True, fill="x")
            ctk.CTkButton(row, text="▶ Play", width=70, height=30,
                          fg_color=ACCENT1, text_color="#000",
                          hover_color="#0099BB", font=ctk.CTkFont(size=11),
                          command=lambda fp=fpath: self._play_file(fp)
                          ).pack(side="right", padx=4)
            ctk.CTkButton(row, text="🗑", width=36, height=30,
                          fg_color="#441111", hover_color="#882222",
                          command=lambda fp=fpath, c=card: self._delete_voice(fp, c)
                          ).pack(side="right", padx=2)

    # ─────────────────────────────────────
    #  DEMO PAGE
    # ─────────────────────────────────────
    def show_demo(self):
        self._clear_content()
        self._set_page("Demo a Character")
        self._back_btn()

        ctk.CTkLabel(self.content, text="▶ Demo a Character",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRI).pack(pady=(20, 4))
        ctk.CTkLabel(self.content,
                     text="Play the reference audio for any trained character.",
                     font=ctk.CTkFont(size=12), text_color=TEXT_SEC
                     ).pack(pady=(0, 20))

        profiles = load_profiles()
        if not profiles:
            ctk.CTkLabel(self.content, text="No characters added yet.",
                         font=ctk.CTkFont(size=13), text_color=TEXT_SEC
                         ).pack(pady=40)
            return

        for p in profiles:
            card = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=14)
            card.pack(fill="x", padx=24, pady=8)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=12)

            photo_path = p.get("photo", "")
            img = make_circle_image(photo_path, 56) if (
                photo_path and os.path.exists(photo_path)) else default_avatar(56)
            ctk.CTkLabel(row, text="", image=img).pack(side="left", padx=(0, 14))

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(info, text=p.get("name", "Unknown"),
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=ACCENT1, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=", ".join(p.get("tags", [])),
                         font=ctk.CTkFont(size=10), text_color=TEXT_SEC,
                         anchor="w").pack(anchor="w")

            ref_path = os.path.join(PROFILES_DIR, p["folder"], "reference.wav")
            has_ref = os.path.exists(ref_path)
            ctk.CTkButton(
                row,
                text="▶ Play Reference" if has_ref else "No audio",
                width=120, height=34,
                fg_color=ACCENT4 if has_ref else "#333344",
                hover_color="#AA3300" if has_ref else "#333344",
                text_color=TEXT_PRI,
                state="normal" if has_ref else "disabled",
                command=lambda rp=ref_path: self._play_file(rp)
            ).pack(side="right")

    # ─────────────────────────────────────
    #  ACTION HANDLERS
    # ─────────────────────────────────────

    def _toggle_recording(self):
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self._recording = True
        self._rec_frames = []
        self._rec_btn.configure(text="⏹  STOP RECORDING", fg_color="#881111")
        self._rec_status.configure(text="🔴 Recording... speak now",
                                    text_color="#FF4444")
        self._conv_btn.configure(state="disabled")

        def record():
            samplerate = 44100
            def callback(indata, frames, time_info, status):
                if self._recording:
                    self._rec_frames.append(indata.copy())
            with sd.InputStream(samplerate=samplerate, channels=1,
                                 dtype='float32', callback=callback):
                while self._recording:
                    time.sleep(0.1)

        self._rec_thread = threading.Thread(target=record, daemon=True)
        self._rec_thread.start()

    def _stop_recording(self):
        self._recording = False
        self._rec_btn.configure(text="⏺  START RECORDING", fg_color="#CC2222")
        self._rec_status.configure(text="✅ Recording saved", text_color=ACCENT3)

        if self._rec_frames:
            audio = np.concatenate(self._rec_frames, axis=0)
            path = os.path.join(TEMP_DIR, "recorded_input.wav")
            sf.write(path, audio, 44100)
            self._recorded_path = path
            self._conv_btn.configure(state="normal")

    def _browse_voice_file(self):
        path = filedialog.askopenfilename(
            title="Select your voice recording",
            filetypes=[("Audio Files", "*.wav *.mp3"), ("All files", "*.*")])
        if path:
            self._selected_file_path = path
            self._file_lbl.configure(
                text=os.path.basename(path), text_color=ACCENT1)
            self._file_conv_btn.configure(state="normal")

    def _pick_train_photo(self):
        path = filedialog.askopenfilename(
            title="Select character photo",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp"),
                       ("All files", "*.*")])
        if path:
            self._train_photo_path = path
            self._train_photo_lbl.configure(
                text=os.path.basename(path), text_color=ACCENT1)

    def _pick_audio_files(self):
        paths = filedialog.askopenfilenames(
            title="Select character voice audio files",
            filetypes=[("Audio Files", "*.wav *.mp3"),
                       ("All files", "*.*")])
        if paths:
            self._train_audio_files = list(paths)
            self._audio_count_lbl.configure(
                text=f"{len(paths)} file(s) selected", text_color=ACCENT3)

    def _start_training(self):
        name = self._train_name.get().strip()
        if not name:
            messagebox.showwarning("VoiceWiz", "Please enter a character name.")
            return
        if not self._train_audio_files:
            messagebox.showwarning("VoiceWiz",
                                   "Please select at least one audio file.")
            return

        tags_raw = self._train_tags.get().strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        self._train_btn.configure(state="disabled", text="Processing...")
        self._train_prog_lbl.configure(text="Starting...")
        self._train_prog.set(0.05)

        threading.Thread(
            target=self._training_pipeline,
            args=(name, tags, self._train_photo_path,
                  self._train_audio_files),
            daemon=True).start()

    def _training_pipeline(self, name, tags, photo_path, audio_files):
        try:
            from training import run_training
            folder = name.lower().replace(" ", "_")
            profile_dir = os.path.join(PROFILES_DIR, folder)
            os.makedirs(profile_dir, exist_ok=True)

            saved_photo = ""
            if photo_path and os.path.exists(photo_path):
                ext = os.path.splitext(photo_path)[1]
                saved_photo = os.path.join(profile_dir, f"photo{ext}")
                shutil.copy2(photo_path, saved_photo)

            def prog(val, msg):
                self.after(0, lambda: self._train_prog.set(val))
                self.after(0, lambda: self._train_prog_lbl.configure(text=msg))

            run_training(audio_files, profile_dir, prog_callback=prog)

            meta = {"name": name, "tags": tags, "photo": saved_photo}
            with open(os.path.join(profile_dir, "meta.json"), "w") as f:
                json.dump(meta, f, indent=2)

            self.after(0, self._training_done)

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.after(0, lambda: self._training_failed(err))

    def _training_done(self):
        self._train_prog.set(1.0)
        self._train_prog_lbl.configure(
            text="✅ Character ready!", text_color=ACCENT3)
        self._train_btn.configure(state="normal", text="🚀  START")
        messagebox.showinfo("VoiceWiz", "Character added successfully!")
        self.show_home()

    def _training_failed(self, err):
        self._train_prog_lbl.configure(
            text=f"Error: {err[:80]}", text_color="#FF4444")
        self._train_btn.configure(state="normal", text="🚀  START")
        messagebox.showerror("VoiceWiz", f"Failed:\n{err[:300]}")

    def _run_conversion(self):
        if not self._recorded_path:
            return
        char_name = self._char_var.get()
        threading.Thread(
            target=self._conversion_pipeline,
            args=(self._recorded_path, char_name,
                  self._prog_bar, self._prog_lbl),
            daemon=True).start()

    def _run_file_conversion(self):
        path = getattr(self, "_selected_file_path", None)
        if not path:
            return
        char_name = self._file_char_var.get()
        threading.Thread(
            target=self._conversion_pipeline,
            args=(path, char_name,
                  self._file_prog_bar, self._file_prog_lbl),
            daemon=True).start()

    def _conversion_pipeline(self, input_path, char_name, prog_bar, prog_lbl):
        try:
            from conversion import run_conversion
            profiles = load_profiles()
            profile = next(
                (p for p in profiles if p.get("name") == char_name), None)
            if not profile:
                self.after(0, lambda: messagebox.showerror(
                    "VoiceWiz", f"Profile '{char_name}' not found."))
                return

            profile_dir = os.path.join(PROFILES_DIR, profile["folder"])

            def prog(val, msg):
                self.after(0, lambda: prog_bar.set(val))
                self.after(0, lambda: prog_lbl.configure(text=msg))

            out_name = f"{char_name}_{int(time.time())}.wav"
            out_path = os.path.join(VOICES_DIR, out_name)

            run_conversion(input_path, profile_dir, out_path,
                           prog_callback=prog)
            self._last_converted = out_path
            self.after(0, lambda: prog_lbl.configure(
                text=f"✅ Saved: {out_name}", text_color=ACCENT3))

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.after(0, lambda: prog_lbl.configure(
                text=f"Error: {str(e)[:80]}", text_color="#FF4444"))
            self.after(0, lambda: messagebox.showerror(
                "VoiceWiz", f"Conversion failed:\n{err[:300]}"))

    def _play_file(self, path):
        if not os.path.exists(path):
            messagebox.showwarning("VoiceWiz", "File not found.")
            return
        def _play():
            data, sr = sf.read(path, dtype='float32')
            sd.play(data, sr)
            sd.wait()
        threading.Thread(target=_play, daemon=True).start()

    def _play_original(self):
        path = getattr(self, "_recorded_path", None) or \
               os.path.join(TEMP_DIR, "recorded_input.wav")
        self._play_file(path)

    def _play_converted(self):
        path = getattr(self, "_last_converted", None)
        if not path:
            messagebox.showinfo("VoiceWiz", "No converted audio yet.")
            return
        self._play_file(path)

    def _delete_profile(self, p):
        if messagebox.askyesno("Delete Character",
                               f"Delete '{p.get('name')}'? This cannot be undone."):
            folder = os.path.join(PROFILES_DIR, p["folder"])
            shutil.rmtree(folder, ignore_errors=True)
            self.show_manage_characters()

    def _delete_voice(self, path, card):
        if messagebox.askyesno("Delete Voice", "Delete this voice file?"):
            os.remove(path)
            card.destroy()


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    app = VoiceWizApp()
    app.mainloop()