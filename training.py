"""
VoiceWiz — Character Setup Pipeline (Seed-VC zero-shot)
No model training needed. Processes and stores reference audio for conversion.
"""

import os, sys, json, time, shutil
import numpy as np
import soundfile as sf
import librosa

# Fix pkg_resources
try:
    import pkg_resources
except Exception:
    import types
    m = types.ModuleType("pkg_resources")
    m.get_distribution = lambda x: None
    m.resource_filename = lambda *a: ""
    m.require = lambda *a: None
    m.DistributionNotFound = Exception
    m.VersionConflict = Exception
    sys.modules["pkg_resources"] = m
    sys.modules["pkg_resources.extern"] = types.ModuleType("pkg_resources.extern")


def _load_audio(fpath, sr=22050):
    """Load any audio file to mono float32."""
    try:
        data, orig_sr = sf.read(fpath, dtype='float32', always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if orig_sr != sr:
            data = librosa.resample(data, orig_sr=orig_sr, target_sr=sr)
        if len(data) > sr * 0.5:
            return data, sr
    except Exception:
        pass
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(fpath).set_frame_rate(sr).set_channels(1)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        samples /= float(2 ** (seg.sample_width * 8 - 1))
        if len(samples) > sr * 0.5:
            return samples, sr
    except Exception as e:
        raise ValueError(f"Cannot load '{os.path.basename(fpath)}': {e}")
    raise ValueError(f"Cannot load '{os.path.basename(fpath)}'")


def _pick_best_segment(audio, sr, target_seconds=20):
    """
    Pick the cleanest segment from audio for use as reference.
    Finds the segment with most consistent RMS energy (most stable voice).
    Seed-VC works best with 10-30 seconds of clean speech.
    """
    target_len = sr * target_seconds
    hop = sr * 5  # 5 second hops

    if len(audio) <= target_len:
        return audio  # Short enough, use all of it

    # Compute RMS energy in windows
    window = sr * 5
    best_score = -1
    best_start = 0

    for start in range(0, len(audio) - target_len, hop):
        segment = audio[start:start + target_len]
        # Score: high mean energy, low variance = stable voice
        rms_per_block = [
            np.sqrt(np.mean(segment[i:i+window]**2))
            for i in range(0, len(segment), window)
            if i + window <= len(segment)
        ]
        if not rms_per_block:
            continue
        mean_rms = np.mean(rms_per_block)
        std_rms = np.std(rms_per_block)
        # Reward high energy, penalise variance
        score = mean_rms / (std_rms + 1e-6)
        if score > best_score and mean_rms > 0.01:  # Must have actual voice
            best_score = score
            best_start = start

    return audio[best_start:best_start + target_len]


def run_training(audio_files, profile_dir, prog_callback=None):
    """
    Process character audio files and prepare reference audio for Seed-VC.
    This is fast — just audio processing, no neural network training.
    """

    def prog(v, msg):
        if prog_callback:
            prog_callback(v, msg)

    prog(0.05, "Preparing character audio...")

    audio_dir = os.path.join(profile_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    SR = 22050
    total = len(audio_files)
    all_audio = []
    processed = 0
    last_error = ""

    # ── Load all audio files ──────────────────────────────────
    for idx, fpath in enumerate(audio_files):
        prog(0.05 + 0.40 * (idx / total),
             f"Loading {idx+1}/{total}: {os.path.basename(fpath)}")
        try:
            audio, sr = _load_audio(fpath, SR)
            # Normalise
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak * 0.90
            all_audio.append(audio)
            # Copy original to audio dir for reference
            ext = os.path.splitext(fpath)[1]
            dest = os.path.join(audio_dir, f"source_{idx:03d}{ext}")
            shutil.copy2(fpath, dest)
            processed += 1
        except Exception as e:
            last_error = str(e)
            continue

    if not all_audio:
        raise ValueError(last_error or "No audio files could be loaded.")

    prog(0.50, "Selecting best voice segment for reference...")

    # ── Concatenate all audio and pick best 20-second segment ──
    combined = np.concatenate(all_audio)

    # Pick the cleanest 20-second segment
    reference_audio = _pick_best_segment(combined, SR, target_seconds=20)

    prog(0.70, "Saving reference audio...")

    # Save as the reference file conversion.py will use
    reference_path = os.path.join(profile_dir, "reference.wav")
    sf.write(reference_path, reference_audio, SR)

    prog(0.80, "Analysing voice characteristics...")

    # ── Extract basic pitch stats for display purposes ────────
    try:
        f0, voiced, _ = librosa.pyin(
            reference_audio, fmin=50, fmax=800, sr=SR)
        voiced_f0 = f0[voiced] if voiced is not None else np.array([])
        f0_mean = float(np.nanmedian(voiced_f0)) if len(voiced_f0) > 0 else 0.0
    except Exception:
        f0_mean = 0.0

    prog(0.90, "Saving profile...")

    # ── Save stats ────────────────────────────────────────────
    stats = {
        "f0_mean":          f0_mean,
        "files_processed":  processed,
        "reference_audio":  reference_path,
        "reference_length": len(reference_audio) / SR,
        "engine":           "seed-vc",
        "trained_at":       time.strftime("%Y-%m-%d %H:%M")
    }
    with open(os.path.join(profile_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    dur = len(reference_audio) / SR
    prog(1.0, f"Done. Reference: {dur:.1f}s of clean voice extracted.")