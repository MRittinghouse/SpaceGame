"""Programmatic SFX generator for SpaceGame.

Generates all sound effects using numpy synthesis — sine waves, noise,
envelopes, and filters. No external audio samples needed.

Usage:
    python tools/generate_sfx.py           # Generate all SFX
    python tools/generate_sfx.py --list    # List all SFX IDs
    python tools/generate_sfx.py ui_click  # Generate specific SFX
"""

import argparse
import json
import struct
import sys
import wave
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.signal import butter, lfilter

# Output settings
SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

OUTPUT_DIR = Path(__file__).parent.parent / "spacegame" / "data" / "assets" / "audio"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


# === Synthesis primitives ===


def sine(freq: float, duration: float, phase: float = 0.0) -> np.ndarray:
    """Generate a sine wave."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t + phase)


def square(freq: float, duration: float) -> np.ndarray:
    """Generate a square wave."""
    return np.sign(sine(freq, duration))


def noise(duration: float) -> np.ndarray:
    """Generate white noise."""
    return np.random.uniform(-1, 1, int(SAMPLE_RATE * duration))


def sweep(f_start: float, f_end: float, duration: float) -> np.ndarray:
    """Generate a frequency sweep (linear)."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(f_start, f_end, len(t))
    phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    return np.sin(phase)


# === Envelope and effects ===


def adsr(
    signal: np.ndarray,
    attack: float = 0.01,
    decay: float = 0.05,
    sustain: float = 0.7,
    release: float = 0.1,
) -> np.ndarray:
    """Apply ADSR envelope to a signal."""
    n = len(signal)
    total_dur = n / SAMPLE_RATE
    env = np.ones(n)

    a_samples = int(attack * SAMPLE_RATE)
    d_samples = int(decay * SAMPLE_RATE)
    r_samples = int(release * SAMPLE_RATE)

    # Attack
    if a_samples > 0:
        env[:a_samples] = np.linspace(0, 1, a_samples)

    # Decay
    d_start = a_samples
    d_end = min(d_start + d_samples, n)
    if d_end > d_start:
        env[d_start:d_end] = np.linspace(1, sustain, d_end - d_start)

    # Sustain
    s_end = max(0, n - r_samples)
    if s_end > d_end:
        env[d_end:s_end] = sustain

    # Release
    if r_samples > 0 and s_end < n:
        env[s_end:] = np.linspace(sustain, 0, n - s_end)

    return signal * env


def fade_in(signal: np.ndarray, duration: float = 0.01) -> np.ndarray:
    """Apply a fade-in."""
    samples = min(int(duration * SAMPLE_RATE), len(signal))
    result = signal.copy()
    result[:samples] *= np.linspace(0, 1, samples)
    return result


def fade_out(signal: np.ndarray, duration: float = 0.05) -> np.ndarray:
    """Apply a fade-out."""
    samples = min(int(duration * SAMPLE_RATE), len(signal))
    result = signal.copy()
    result[-samples:] *= np.linspace(1, 0, samples)
    return result


def lowpass(signal: np.ndarray, cutoff: float, order: int = 4) -> np.ndarray:
    """Apply a low-pass filter."""
    nyq = SAMPLE_RATE / 2
    cutoff = min(cutoff, nyq * 0.99)
    b, a = butter(order, cutoff / nyq, btype="low")
    return lfilter(b, a, signal)


def highpass(signal: np.ndarray, cutoff: float, order: int = 4) -> np.ndarray:
    """Apply a high-pass filter."""
    nyq = SAMPLE_RATE / 2
    cutoff = min(cutoff, nyq * 0.99)
    b, a = butter(order, cutoff / nyq, btype="high")
    return lfilter(b, a, signal)


def reverb(signal: np.ndarray, decay: float = 0.3, delay_ms: float = 30) -> np.ndarray:
    """Simple echo-based reverb."""
    delay_samples = int(delay_ms * SAMPLE_RATE / 1000)
    result = signal.copy()
    for i in range(1, 5):
        offset = delay_samples * i
        gain = decay ** i
        if offset < len(result):
            result[offset:] += signal[: len(result) - offset] * gain
    return np.clip(result, -1, 1)


def bitcrush(signal: np.ndarray, bits: int = 4) -> np.ndarray:
    """Reduce bit depth for retro/glitch effect."""
    levels = 2 ** bits
    return np.round(signal * levels) / levels


def mix(*signals: np.ndarray) -> np.ndarray:
    """Mix multiple signals, zero-padding to longest."""
    max_len = max(len(s) for s in signals)
    result = np.zeros(max_len)
    for s in signals:
        result[: len(s)] += s
    return np.clip(result, -1, 1)


def concat(*signals: np.ndarray) -> np.ndarray:
    """Concatenate signals end-to-end."""
    return np.concatenate(signals)


def normalize(signal: np.ndarray, peak: float = 0.9) -> np.ndarray:
    """Normalize signal to peak amplitude."""
    mx = np.max(np.abs(signal))
    if mx > 0:
        return signal * (peak / mx)
    return signal


def save_wav(signal: np.ndarray, path: Path) -> None:
    """Save signal as 16-bit WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    signal = normalize(signal)
    data = (signal * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data.tobytes())


# === SFX Generators ===

# Each returns (np.ndarray, category, default_volume)


def gen_ui_click() -> tuple[np.ndarray, str, float]:
    sig = mix(sine(800, 0.03) * 0.6, sine(1200, 0.03) * 0.3)
    sig = adsr(sig, attack=0.001, decay=0.02, sustain=0.0, release=0.01)
    return sig, "ui", 0.7


def gen_ui_hover() -> tuple[np.ndarray, str, float]:
    sig = sine(600, 0.02) * 0.3
    sig = adsr(sig, attack=0.002, decay=0.01, sustain=0.0, release=0.008)
    return sig, "ui", 0.4


def gen_ui_confirm() -> tuple[np.ndarray, str, float]:
    t1 = adsr(sine(400, 0.06), attack=0.002, decay=0.03, sustain=0.5, release=0.02)
    t2 = adsr(sine(600, 0.06), attack=0.002, decay=0.03, sustain=0.5, release=0.02)
    sig = concat(t1, t2)
    return sig, "ui", 0.7


def gen_ui_cancel() -> tuple[np.ndarray, str, float]:
    t1 = adsr(sine(600, 0.06), attack=0.002, decay=0.03, sustain=0.5, release=0.02)
    t2 = adsr(sine(400, 0.06), attack=0.002, decay=0.03, sustain=0.5, release=0.02)
    sig = concat(t1, t2)
    return sig, "ui", 0.7


def gen_ui_error() -> tuple[np.ndarray, str, float]:
    sig = square(200, 0.15) * 0.4
    sig = adsr(sig, attack=0.005, decay=0.05, sustain=0.6, release=0.05)
    sig = lowpass(sig, 2000)
    return sig, "ui", 0.6


def gen_ui_scroll() -> tuple[np.ndarray, str, float]:
    sig = noise(0.01) * 0.3
    sig = adsr(sig, attack=0.001, decay=0.005, sustain=0.0, release=0.004)
    sig = highpass(sig, 2000)
    return sig, "ui", 0.3


def gen_trade_buy() -> tuple[np.ndarray, str, float]:
    # Ka-ching: two ascending tones + metallic noise
    t1 = adsr(sine(880, 0.08), attack=0.002, decay=0.04, sustain=0.3, release=0.03)
    t2 = adsr(sine(1320, 0.12), attack=0.002, decay=0.06, sustain=0.3, release=0.04)
    ring = adsr(sine(2640, 0.15) * 0.3, attack=0.001, decay=0.1, sustain=0.0, release=0.05)
    n = highpass(noise(0.04) * 0.2, 4000)
    body = concat(t1, t2)
    sig = mix(body, ring)
    sig = mix(sig, fade_in(n, 0.001))
    sig = reverb(sig, decay=0.2, delay_ms=20)
    return sig, "trading", 0.8


def gen_trade_sell() -> tuple[np.ndarray, str, float]:
    # Coin drop: descending metallic ping
    sig = sweep(1500, 800, 0.15) * 0.6
    ring = sine(1200, 0.2) * 0.3
    sig = adsr(mix(sig, ring), attack=0.002, decay=0.1, sustain=0.1, release=0.08)
    sig = reverb(sig, decay=0.25, delay_ms=15)
    return sig, "trading", 0.8


def gen_trade_fail() -> tuple[np.ndarray, str, float]:
    sig = sweep(400, 200, 0.15)
    buzz = square(150, 0.1) * 0.3
    sig = adsr(mix(sig, buzz), attack=0.005, decay=0.08, sustain=0.3, release=0.06)
    return sig, "trading", 0.7


def gen_trade_refuel() -> tuple[np.ndarray, str, float]:
    # Rising hiss
    n = noise(1.0)
    n = highpass(n, 1000)
    env = np.linspace(0.1, 0.6, len(n))
    sig = n * env
    sig = fade_out(sig, 0.15)
    return sig, "trading", 0.5


def gen_mine_click() -> tuple[np.ndarray, str, float]:
    impact = noise(0.02) * 0.7
    ring = adsr(sine(300, 0.05), attack=0.001, decay=0.03, sustain=0.0, release=0.02)
    sig = mix(impact, ring)
    sig = highpass(sig, 100)
    return sig, "mining", 0.8


def gen_mine_drill() -> tuple[np.ndarray, str, float]:
    # Looping rumble — 2 seconds
    base = sine(120, 2.0) * 0.4
    n = lowpass(noise(2.0) * 0.3, 500)
    mod = sine(8, 2.0) * 0.3 + 0.7  # Amplitude modulation
    sig = (base + n) * mod
    sig = fade_in(sig, 0.1)
    sig = fade_out(sig, 0.1)
    return sig, "mining", 0.5


def gen_mine_break() -> tuple[np.ndarray, str, float]:
    crack = noise(0.05) * 0.8
    rumble = lowpass(noise(0.15), 600) * 0.5
    ring = adsr(sine(200, 0.1), attack=0.002, decay=0.05, sustain=0.0, release=0.05)
    sig = mix(concat(crack, rumble * 0.5), ring)
    sig = fade_out(sig, 0.05)
    return sig, "mining", 0.8


def gen_mine_chain() -> tuple[np.ndarray, str, float]:
    # Rapid ascending pops
    pops = []
    for i in range(5):
        freq = 250 + i * 80
        pop = adsr(sine(freq, 0.04) + noise(0.04) * 0.3, attack=0.002, decay=0.02, sustain=0.0, release=0.02)
        pops.append(pop)
        if i < 4:
            pops.append(np.zeros(int(0.03 * SAMPLE_RATE)))
    sig = concat(*pops)
    return sig, "mining", 0.8


def gen_mine_collect() -> tuple[np.ndarray, str, float]:
    # Bright chime
    t1 = sine(880, 0.15) * 0.5
    t2 = sine(1320, 0.15) * 0.3
    t3 = sine(1760, 0.1) * 0.2
    sig = adsr(mix(t1, t2, t3), attack=0.003, decay=0.08, sustain=0.2, release=0.06)
    sig = reverb(sig, decay=0.2, delay_ms=25)
    return sig, "mining", 0.7


def gen_mine_energy() -> tuple[np.ndarray, str, float]:
    sig = sweep(200, 800, 0.3) * 0.5
    sig = adsr(sig, attack=0.02, decay=0.1, sustain=0.5, release=0.15)
    return sig, "mining", 0.6


def gen_combat_laser() -> tuple[np.ndarray, str, float]:
    sig = sweep(2000, 500, 0.1) * 0.7
    sig = adsr(sig, attack=0.002, decay=0.05, sustain=0.3, release=0.04)
    sig = reverb(sig, decay=0.15, delay_ms=10)
    return sig, "combat", 0.9


def gen_combat_hit() -> tuple[np.ndarray, str, float]:
    thump = adsr(sine(80, 0.15), attack=0.003, decay=0.08, sustain=0.0, release=0.06)
    crack = adsr(noise(0.08) * 0.6, attack=0.001, decay=0.04, sustain=0.0, release=0.04)
    sig = mix(thump, crack)
    return sig, "combat", 0.9


def gen_combat_shield() -> tuple[np.ndarray, str, float]:
    # Metallic ring with harmonics
    f1 = sine(1200, 0.25) * 0.5
    f2 = sine(1800, 0.2) * 0.3
    f3 = sine(2400, 0.15) * 0.15
    sig = adsr(mix(f1, f2, f3), attack=0.005, decay=0.15, sustain=0.1, release=0.1)
    sig = reverb(sig, decay=0.3, delay_ms=20)
    return sig, "combat", 0.8


def gen_combat_missile() -> tuple[np.ndarray, str, float]:
    whoosh = sweep(300, 1500, 0.3) * 0.5
    n = highpass(noise(0.3), 500) * 0.3
    sig = adsr(mix(whoosh, n), attack=0.01, decay=0.1, sustain=0.5, release=0.15)
    return sig, "combat", 0.8


def gen_combat_explosion() -> tuple[np.ndarray, str, float]:
    # Layered noise bursts
    boom = lowpass(noise(0.5), 400) * 0.8
    crack = noise(0.1) * 0.6
    sub = sine(40, 0.4) * 0.5
    sig = mix(boom, crack, sub)
    sig = adsr(sig, attack=0.005, decay=0.2, sustain=0.2, release=0.25)
    return sig, "combat", 0.9


def gen_combat_victory() -> tuple[np.ndarray, str, float]:
    # Major chord arpeggio C-E-G-C
    notes = [
        adsr(sine(523, 0.2), attack=0.01, decay=0.08, sustain=0.5, release=0.08),
        adsr(sine(659, 0.2), attack=0.01, decay=0.08, sustain=0.5, release=0.08),
        adsr(sine(784, 0.2), attack=0.01, decay=0.08, sustain=0.5, release=0.08),
        adsr(sine(1047, 0.3), attack=0.01, decay=0.1, sustain=0.5, release=0.15),
    ]
    sig = notes[0]
    for n in notes[1:]:
        gap = np.zeros(int(0.02 * SAMPLE_RATE))
        sig = concat(sig, gap, n)
    sig = reverb(sig, decay=0.25, delay_ms=30)
    return sig, "combat", 0.8


def gen_combat_defeat() -> tuple[np.ndarray, str, float]:
    # Minor chord descending Am
    notes = [
        adsr(sine(880, 0.25), attack=0.01, decay=0.1, sustain=0.4, release=0.1),
        adsr(sine(659, 0.25), attack=0.01, decay=0.1, sustain=0.4, release=0.1),
        adsr(sine(523, 0.35), attack=0.01, decay=0.15, sustain=0.3, release=0.15),
    ]
    sig = notes[0]
    for n in notes[1:]:
        gap = np.zeros(int(0.03 * SAMPLE_RATE))
        sig = concat(sig, gap, n)
    sig = reverb(sig, decay=0.3, delay_ms=35)
    return sig, "combat", 0.8


def gen_salvage_scan() -> tuple[np.ndarray, str, float]:
    # Sonar ping
    sig = sine(1000, 0.08) * 0.7
    sig = adsr(sig, attack=0.005, decay=0.04, sustain=0.0, release=0.03)
    sig = reverb(sig, decay=0.4, delay_ms=40)
    # Extend with reverb tail
    tail = np.zeros(int(0.3 * SAMPLE_RATE))
    sig = concat(sig, tail)
    sig = reverb(sig, decay=0.3, delay_ms=50)
    return sig, "salvage", 0.7


def gen_salvage_reveal() -> tuple[np.ndarray, str, float]:
    t1 = sine(600, 0.05)
    t2 = sine(900, 0.05)
    sig = adsr(concat(t1, t2), attack=0.003, decay=0.04, sustain=0.2, release=0.03)
    return sig, "salvage", 0.7


def gen_salvage_extract() -> tuple[np.ndarray, str, float]:
    # Mechanical whir
    base = sine(150, 0.3) * 0.3
    mod = sine(12, 0.3)
    n = lowpass(noise(0.3), 2000) * 0.3
    sig = (base * (0.5 + 0.5 * mod)) + n
    sig = adsr(sig, attack=0.02, decay=0.1, sustain=0.6, release=0.15)
    return sig, "salvage", 0.7


def gen_salvage_corrupt() -> tuple[np.ndarray, str, float]:
    sig = noise(0.2) * 0.6
    sig = bitcrush(sig, bits=3)
    sig = adsr(sig, attack=0.005, decay=0.08, sustain=0.3, release=0.08)
    sig = lowpass(sig, 3000)
    return sig, "salvage", 0.6


def gen_nav_jump() -> tuple[np.ndarray, str, float]:
    # Rising sweep + noise
    swp = sweep(100, 4000, 0.6) * 0.5
    n = highpass(noise(0.6), 500) * 0.3
    env = np.linspace(0.3, 1.0, len(swp))
    sig = (swp + n) * env
    sig = fade_out(sig, 0.1)
    return sig, "navigation", 0.8


def gen_nav_arrive() -> tuple[np.ndarray, str, float]:
    swp = sweep(2000, 400, 0.4) * 0.5
    sig = adsr(swp, attack=0.01, decay=0.15, sustain=0.3, release=0.2)
    sig = reverb(sig, decay=0.3, delay_ms=30)
    return sig, "navigation", 0.7


def gen_nav_select() -> tuple[np.ndarray, str, float]:
    sig = sine(1000, 0.05) * 0.5
    sig = adsr(sig, attack=0.003, decay=0.03, sustain=0.0, release=0.02)
    return sig, "navigation", 0.6


def gen_nav_encounter() -> tuple[np.ndarray, str, float]:
    # Two-tone alarm
    t1 = sine(600, 0.12)
    t2 = sine(800, 0.12)
    sig = concat(t1, t2, t1, t2) * 0.6
    sig = adsr(sig, attack=0.005, decay=0.05, sustain=0.7, release=0.05)
    return sig, "navigation", 0.8


def gen_nav_dock() -> tuple[np.ndarray, str, float]:
    # Mechanical clunk + hiss
    clunk = lowpass(noise(0.05) * 0.7, 800)
    thud = adsr(sine(100, 0.08), attack=0.003, decay=0.04, sustain=0.0, release=0.04)
    hiss = highpass(noise(0.2), 3000) * 0.2
    hiss = fade_in(hiss, 0.05)
    hiss = fade_out(hiss, 0.1)
    sig = mix(concat(mix(clunk, thud), hiss[:int(0.2 * SAMPLE_RATE)]))
    return sig, "navigation", 0.7


def gen_ground_step() -> tuple[np.ndarray, str, float]:
    sig = lowpass(noise(0.04), 1200) * 0.5
    sig = adsr(sig, attack=0.002, decay=0.02, sustain=0.0, release=0.02)
    return sig, "ground", 0.5


def gen_ground_door() -> tuple[np.ndarray, str, float]:
    # Mechanical slide
    n = noise(0.3)
    n = lowpass(n, 2000)
    env = np.concatenate([np.linspace(0, 0.5, int(0.1 * SAMPLE_RATE)),
                          np.linspace(0.5, 0.3, int(0.1 * SAMPLE_RATE)),
                          np.linspace(0.3, 0.0, int(0.1 * SAMPLE_RATE))])
    sig = n[:len(env)] * env
    return sig, "ground", 0.6


def gen_ground_alert() -> tuple[np.ndarray, str, float]:
    sig = sweep(400, 900, 0.4) * 0.6
    sig = adsr(sig, attack=0.01, decay=0.1, sustain=0.5, release=0.2)
    return sig, "ground", 0.7


def gen_ground_pickup() -> tuple[np.ndarray, str, float]:
    t1 = sine(800, 0.05)
    t2 = sine(1200, 0.05)
    sig = adsr(concat(t1, t2), attack=0.003, decay=0.04, sustain=0.2, release=0.02)
    return sig, "ground", 0.7


def gen_ground_combat() -> tuple[np.ndarray, str, float]:
    # Tension stinger: dissonant chord
    f1 = sine(220, 0.3) * 0.4
    f2 = sine(277, 0.3) * 0.3  # Tritone-ish
    f3 = sine(330, 0.25) * 0.2
    sig = adsr(mix(f1, f2, f3), attack=0.01, decay=0.15, sustain=0.3, release=0.1)
    sig = reverb(sig, decay=0.3, delay_ms=25)
    return sig, "ground", 0.8


def gen_refine_start() -> tuple[np.ndarray, str, float]:
    base = sine(80, 1.0) * 0.3
    n = lowpass(noise(1.0), 400) * 0.3
    mod = sine(3, 1.0) * 0.2 + 0.8
    sig = (base + n) * mod
    sig = fade_in(sig, 0.15)
    sig = fade_out(sig, 0.15)
    return sig, "activity", 0.5


def gen_refine_complete() -> tuple[np.ndarray, str, float]:
    t1 = sine(523, 0.08)
    t2 = sine(659, 0.08)
    t3 = sine(784, 0.12)
    sig = adsr(concat(t1, t2, t3), attack=0.005, decay=0.05, sustain=0.4, release=0.06)
    sig = reverb(sig, decay=0.2, delay_ms=20)
    return sig, "activity", 0.7


def gen_repair_weld() -> tuple[np.ndarray, str, float]:
    # Crackling arc
    n = noise(0.4) * 0.5
    n = highpass(n, 1000)
    # Random amplitude modulation for crackle effect
    mod = np.random.uniform(0.2, 1.0, len(n))
    mod = lowpass(mod, 30)
    sig = n * mod
    sig = fade_in(sig, 0.03)
    sig = fade_out(sig, 0.1)
    return sig, "activity", 0.6


def gen_skill_unlock() -> tuple[np.ndarray, str, float]:
    # Ascending fifth C→G
    t1 = adsr(sine(523, 0.15), attack=0.01, decay=0.06, sustain=0.5, release=0.05)
    t2 = adsr(sine(784, 0.25), attack=0.01, decay=0.1, sustain=0.4, release=0.1)
    sparkle = adsr(sine(1568, 0.15) * 0.2, attack=0.05, decay=0.05, sustain=0.1, release=0.05)
    sig = concat(t1, t2)
    # Offset sparkle to start partway through
    offset = int(0.15 * SAMPLE_RATE)
    padded = np.zeros(len(sig))
    end = min(offset + len(sparkle), len(sig))
    padded[offset:end] = sparkle[: end - offset]
    sig = mix(sig, padded)
    sig = reverb(sig, decay=0.2, delay_ms=25)
    return sig, "activity", 0.8


def gen_achievement() -> tuple[np.ndarray, str, float]:
    # Special ascending arpeggio + shimmer
    freqs = [523, 659, 784, 1047, 1319]
    parts = []
    for i, f in enumerate(freqs):
        dur = 0.1 if i < 4 else 0.2
        note = adsr(sine(f, dur), attack=0.005, decay=0.04, sustain=0.4, release=0.05)
        parts.append(note)
        if i < 4:
            parts.append(np.zeros(int(0.02 * SAMPLE_RATE)))
    sig = concat(*parts)
    shimmer = sine(2637, 0.3) * 0.15
    shimmer = adsr(shimmer, attack=0.05, decay=0.1, sustain=0.1, release=0.1)
    # Offset shimmer
    offset = int(0.2 * SAMPLE_RATE)
    padded = np.zeros(len(sig))
    end = min(offset + len(shimmer), len(sig))
    padded[offset:end] = shimmer[: end - offset]
    sig = mix(sig, padded)
    sig = reverb(sig, decay=0.25, delay_ms=30)
    return sig, "activity", 0.8


# === Ambient loops ===


def gen_ambient_station() -> tuple[np.ndarray, str, float]:
    duration = 8.0
    # Low drone
    drone = sine(60, duration) * 0.2
    # Distant machinery
    mach = lowpass(noise(duration), 300) * 0.15
    mod = sine(0.3, duration) * 0.5 + 0.5
    mach = mach * mod
    sig = mix(drone, mach)
    sig = fade_in(sig, 0.5)
    sig = fade_out(sig, 0.5)
    return sig, "ambient", 0.5


def gen_ambient_space() -> tuple[np.ndarray, str, float]:
    duration = 10.0
    # Very low filtered noise
    n = lowpass(noise(duration), 200) * 0.15
    # Subtle sine drift
    drift = sine(40, duration) * 0.1
    mod = sine(0.1, duration) * 0.3 + 0.7
    sig = (n + drift) * mod
    sig = fade_in(sig, 1.0)
    sig = fade_out(sig, 1.0)
    return sig, "ambient", 0.4


def gen_ambient_ground() -> tuple[np.ndarray, str, float]:
    duration = 8.0
    # Tense low pad
    pad = sine(55, duration) * 0.15 + sine(82, duration) * 0.1
    n = lowpass(noise(duration), 400) * 0.1
    mod = sine(0.2, duration) * 0.3 + 0.7
    sig = (pad + n) * mod
    sig = fade_in(sig, 0.5)
    sig = fade_out(sig, 0.5)
    return sig, "ambient", 0.4


def gen_ambient_combat() -> tuple[np.ndarray, str, float]:
    duration = 4.0
    # Pulsing low drone at ~120bpm = 2Hz
    drone = sine(50, duration) * 0.3
    pulse = sine(2, duration) * 0.4 + 0.6
    n = lowpass(noise(duration), 500) * 0.15
    sig = (drone + n) * pulse
    sig = fade_in(sig, 0.2)
    sig = fade_out(sig, 0.2)
    return sig, "ambient", 0.5


# === Registry ===

SFX_REGISTRY: dict[str, Callable[[], tuple[np.ndarray, str, float]]] = {
    # UI
    "ui_click": gen_ui_click,
    "ui_hover": gen_ui_hover,
    "ui_confirm": gen_ui_confirm,
    "ui_cancel": gen_ui_cancel,
    "ui_error": gen_ui_error,
    "ui_scroll": gen_ui_scroll,
    # Trading
    "trade_buy": gen_trade_buy,
    "trade_sell": gen_trade_sell,
    "trade_fail": gen_trade_fail,
    "trade_refuel": gen_trade_refuel,
    # Mining
    "mine_click": gen_mine_click,
    "mine_drill": gen_mine_drill,
    "mine_break": gen_mine_break,
    "mine_chain": gen_mine_chain,
    "mine_collect": gen_mine_collect,
    "mine_energy": gen_mine_energy,
    # Combat
    "combat_laser": gen_combat_laser,
    "combat_hit": gen_combat_hit,
    "combat_shield": gen_combat_shield,
    "combat_missile": gen_combat_missile,
    "combat_explosion": gen_combat_explosion,
    "combat_victory": gen_combat_victory,
    "combat_defeat": gen_combat_defeat,
    # Salvage
    "salvage_scan": gen_salvage_scan,
    "salvage_reveal": gen_salvage_reveal,
    "salvage_extract": gen_salvage_extract,
    "salvage_corrupt": gen_salvage_corrupt,
    # Navigation
    "nav_jump": gen_nav_jump,
    "nav_arrive": gen_nav_arrive,
    "nav_select": gen_nav_select,
    "nav_encounter": gen_nav_encounter,
    "nav_dock": gen_nav_dock,
    # Ground
    "ground_step": gen_ground_step,
    "ground_door": gen_ground_door,
    "ground_alert": gen_ground_alert,
    "ground_pickup": gen_ground_pickup,
    "ground_combat": gen_ground_combat,
    # Activities
    "refine_start": gen_refine_start,
    "refine_complete": gen_refine_complete,
    "repair_weld": gen_repair_weld,
    "skill_unlock": gen_skill_unlock,
    "achievement": gen_achievement,
    # Ambient
    "ambient_station": gen_ambient_station,
    "ambient_space": gen_ambient_space,
    "ambient_ground": gen_ambient_ground,
    "ambient_combat": gen_ambient_combat,
}

# Category → subdirectory mapping
CATEGORY_DIRS = {
    "ui": "sfx/ui",
    "trading": "sfx/trading",
    "mining": "sfx/mining",
    "combat": "sfx/combat",
    "salvage": "sfx/salvage",
    "navigation": "sfx/navigation",
    "ground": "sfx/ground",
    "activity": "sfx/activity",
    "ambient": "ambient",
}


def generate_all(ids: list[str] | None = None) -> dict:
    """Generate SFX files and return manifest data.

    Args:
        ids: Specific SFX IDs to generate. None = all.

    Returns:
        Manifest dict with sfx/ambient entries.
    """
    manifest: dict[str, dict] = {"sfx": {}, "music": {}, "ambient": {}}
    targets = ids if ids else list(SFX_REGISTRY.keys())

    for sfx_id in targets:
        if sfx_id not in SFX_REGISTRY:
            print(f"  SKIP unknown: {sfx_id}")
            continue

        gen_func = SFX_REGISTRY[sfx_id]
        signal, category, default_volume = gen_func()

        subdir = CATEGORY_DIRS.get(category, f"sfx/{category}")
        rel_path = f"{subdir}/{sfx_id}.wav"
        out_path = OUTPUT_DIR / rel_path

        save_wav(signal, out_path)

        section = "ambient" if category == "ambient" else "sfx"
        manifest[section][sfx_id] = {"file": rel_path, "volume": default_volume}
        print(f"  OK {sfx_id} -> {rel_path} ({len(signal)} samples)")

    return manifest


def write_manifest(manifest: dict) -> None:
    """Write or merge manifest to manifest.json."""
    # Load existing manifest if present
    existing: dict = {"sfx": {}, "music": {}, "ambient": {}}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r") as f:
            existing = json.load(f)

    # Merge new entries
    for section in ("sfx", "music", "ambient"):
        existing.setdefault(section, {}).update(manifest.get(section, {}))

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(existing, f, indent=2, sort_keys=True)
    print(f"\nManifest written to {MANIFEST_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SpaceGame SFX")
    parser.add_argument("ids", nargs="*", help="Specific SFX IDs to generate (default: all)")
    parser.add_argument("--list", action="store_true", help="List all available SFX IDs")
    args = parser.parse_args()

    if args.list:
        for sfx_id in sorted(SFX_REGISTRY.keys()):
            print(f"  {sfx_id}")
        print(f"\nTotal: {len(SFX_REGISTRY)} SFX")
        return

    ids = args.ids if args.ids else None
    count = len(ids) if ids else len(SFX_REGISTRY)
    print(f"Generating {count} SFX...")
    manifest = generate_all(ids)
    write_manifest(manifest)
    print(f"Done! {count} SFX generated.")


if __name__ == "__main__":
    main()
