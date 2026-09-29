# VoiceWiz 🎙️

![Python](https://img.shields.io/badge/Python-3.12-blue)
![CPU Only](https://img.shields.io/badge/CPU-Only-green)
![Free](https://img.shields.io/badge/100%25-Free-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

Suppose you want to make dialogues or voice lines for your audiobook, small content, or personal project — but AI voices sound dead? Voice converters cost money? Well look no further. **VoiceWiz is the right tool for you.**

VoiceWiz is a local voice changer where you can train your own character voices with even a 10 second clip (though longer clips give better results), and once the profile is created, you can record your own voice or drop a `.wav`/`.mp3` file and watch it convert. No internet, no paywall, no "log into this" API drama. It runs strictly on your computer's CPU, processing your sample voice through **Seed-VC** and using **OpenAI's Whisper Small** model to detect and convert your voice. The cleaner your recording, the better the result.

This tool is handy for those who want lively voices with emotion instead of robotic AI-generated ones — and it's specially made for people who cannot afford a voice actor.

> **Note:** The process is slow and works on CPU only. Apologies to those with an NVIDIA or AMD GPU — I don't have one to properly test and implement GPU support.

---

## ⚠️ Critical Notice

This project is **NOT** made for replacing voice actors or diminishing their talents. It is a tool for those who have constraints. If you have the capability, I strongly encourage you to support someone with genuine talent instead of using AI tools.

This tool is **not** made for copying voice actors, breaching copyright laws, or plagiarism. The developer is **not responsible** for any action the user takes — those decisions are made by the user. This tool is not to be used for morally questionable works, and I highly encourage you to use it only when you hit a wall.

---

## 📥 Installation

### Step 1 — Run the Installer

Tap `VoiceWiz_Setup.exe`, choose where you want to install, then hit Install. Everything else is handled automatically.

![Installation Step 1](image1.png)
![Installation Step 2](image2.png)

### Step 2 — Internet Required for Setup

The installer downloads the following during setup:

**Python packages (~500MB total)**
| Package | Version |
|---------|---------|
| numpy | 1.26.4 |
| torch (CPU) | 2.4.0 (~200MB) |
| torchaudio | 2.4.0 |
| scipy | 1.13.1 |
| librosa | 0.10.2 |
| soundfile | latest |
| sounddevice | latest |
| pydub | latest |
| customtkinter | latest |
| Pillow | latest |
| munch | 4.0.0 |
| einops | 0.8.0 |
| praat-parselmouth | latest |
| pyworld | latest |
| resemblyzer | latest |
| descript-audio-codec | latest |
| transformers | 4.46.3 |
| huggingface-hub | latest |

**From GitHub**
- seed-vc repository (~70MB)

**Downloaded on first conversion only (~1GB)**
| Model | Size |
|-------|------|
| Seed-VC DiT model | 440MB |
| BigVGAN vocoder | 449MB |
| Whisper Small (content encoder) | 360MB |
| CampPlus speaker model | 28MB |

> **Total initial setup: ~2GB** — all stored in the folder you chose during installation. After this, everything works completely offline.

---

## 🎓 How to Train a Character

1. Open the app
2. Click **"Train a New Character"**

![Train menu](image3.png)

3. Enter your character name, add tags, and optionally add a photo for identification

![Character details](image4.png)

4. Select a valid audio file (`WAV` or `MP3`) — anywhere from 10 seconds to 30 minutes

![Audio selection](image5.png)

5. Click **Start**

![Start training](image6.png)

6. Once training is done you will see a success message

![Training complete](image7.png)

7. Go back to the main menu and your character profile will appear at the bottom

---

## 🔊 How to Convert a Voice

> I am still working on the **Record Your Voice** option. Until that is fixed, please use a pre-recorded file.

1. Choose **"Select a Recorded File"** from the main menu
2. Click **"Browse File"** to select your recorded voice

![Browse file](image8.png)

3. Click the dropdown under **"Convert to"** and select your character
4. Click **Convert Voice**
5. Once done, find your file under **"Manage Created Voices"** — or directly in your install folder at:

```
...\VoiceWiz\voices\
```

![Output](image9.png)

---

## 🛠️ Tech Stack

- [Seed-VC](https://github.com/Plachtaa/seed-vc) — Zero-shot voice conversion
- [OpenAI Whisper Small](https://github.com/openai/whisper) — Content encoder
- [BigVGAN](https://github.com/NVIDIA/BigVGAN) — Neural vocoder
- [PyTorch 2.4.0 CPU](https://pytorch.org/) — Deep learning backend
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — UI framework

---

## 📋 Requirements

- Windows 10 or 11 (64-bit)
- Internet connection (first setup only)
- ~2GB free disk space
- No GPU required

---

*And don't forget to have fun! I wish you success in whatever you are making and I hope this helped.* 🎉
