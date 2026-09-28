"""
VoiceWiz — Seed-VC Conversion Pipeline
Runs inference.py from cloned seed-vc as a subprocess to avoid thread conflicts.
"""

import os, sys, json, time, shutil, subprocess
import numpy as np
import soundfile as sf
import librosa


def _load_audio(path, sr=22050):
    try:
        data, orig_sr = sf.read(path, dtype='float32', always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if orig_sr != sr:
            data = librosa.resample(data, orig_sr=orig_sr, target_sr=sr)
        return data
    except Exception:
        pass
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(path).set_frame_rate(sr).set_channels(1)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        samples /= float(2 ** (seg.sample_width * 8 - 1))
        return samples
    except Exception as e:
        raise ValueError(f"Cannot load audio: {e}")


def _get_seedvc_dir():
    """Find the cloned seed-vc directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base, "seed-vc")
    if os.path.exists(os.path.join(candidate, "inference.py")):
        return candidate
    raise FileNotFoundError(
        "seed-vc folder not found. Make sure E:\\VoiceWiz\\seed-vc exists.")


def _get_reference_audio(profile_dir):
    """Get reference audio path for this character."""
    ref = os.path.join(profile_dir, "reference.wav")
    if os.path.exists(ref):
        return ref

    # Try finding any audio in audio subfolder
    audio_dir = os.path.join(profile_dir, "audio")
    if os.path.exists(audio_dir):
        for f in os.listdir(audio_dir):
            if f.lower().endswith(('.wav', '.mp3', '.flac', '.m4a')):
                src = os.path.join(audio_dir, f)
                audio = _load_audio(src, sr=22050)
                target_len = 22050 * 20
                if len(audio) > target_len:
                    start = (len(audio) - target_len) // 2
                    audio = audio[start:start + target_len]
                sf.write(ref, audio, 22050)
                return ref

    raise FileNotFoundError(
        "No reference audio found for this character. "
        "Please re-add the character with audio files.")


def run_conversion(input_path, profile_dir, output_path, prog_callback=None):

    def prog(v, msg):
        if prog_callback:
            prog_callback(v, msg)

    prog(0.05, "Finding character reference audio...")
    reference_path = _get_reference_audio(profile_dir)

    prog(0.10, "Locating Seed-VC engine...")
    seedvc_dir = _get_seedvc_dir()
    inference_script = os.path.join(seedvc_dir, "inference.py")

    # Ensure source is WAV
    prog(0.15, "Preparing input audio...")
    if not input_path.lower().endswith('.wav'):
        audio = _load_audio(input_path, sr=22050)
        wav_path = os.path.join(
            os.path.dirname(output_path), "_input_tmp.wav")
        sf.write(wav_path, audio, 22050)
        source_path = wav_path
    else:
        source_path = input_path

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    prog(0.20, "Starting Seed-VC (first run downloads ~500MB model)...")

    # Get the python executable from our venv
    python_exe = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "venv", "Scripts", "python.exe")

    if not os.path.exists(python_exe):
        python_exe = sys.executable

    cmd = [
        python_exe,
        inference_script,
        "--source", source_path,
        "--target", reference_path,
        "--output", output_dir,
        "--diffusion-steps", "10",
        "--inference-cfg-rate", "0.7",
        "--fp16", "False",
    ]

    prog(0.25, "Running voice conversion (this takes a few minutes on CPU)...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=seedvc_dir,
            timeout=1800  # 30 minute timeout
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Conversion timed out after 30 minutes.")

    if result.returncode != 0:
        # Show last 600 chars of stderr for diagnosis
        err = result.stderr[-600:] if result.stderr else "Unknown error"
        raise RuntimeError(f"Seed-VC conversion failed:\n{err}")

    prog(0.90, "Saving output file...")

    # seed-vc names output: vc_{source}_{target}_{length}_{steps}_{cfg}.wav
    source_stem = os.path.splitext(os.path.basename(source_path))[0]
    found = None

    # Check seed-vc's default output folder inside its own directory
    seedvc_output = os.path.join(seedvc_dir, "reconstructed")
    search_dirs = [output_dir, seedvc_output]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for f in os.listdir(search_dir):
            if f.endswith('.wav') and f.startswith('vc_'):
                found = os.path.join(search_dir, f)
                break
        if found:
            break

    # Final fallback: newest wav anywhere in output or seedvc dirs
    if not found:
        all_wavs = []
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                all_wavs += [
                    os.path.join(search_dir, f)
                    for f in os.listdir(search_dir)
                    if f.endswith('.wav')
                ]
        if all_wavs:
            found = max(all_wavs, key=os.path.getmtime)

    if found and os.path.exists(found):
        shutil.move(found, output_path)
    else:
        raise FileNotFoundError(
            "Seed-VC ran but no output WAV was found. "
            "Check your reference audio contains clean speech with no background music.")

    prog(1.0, "Done.")