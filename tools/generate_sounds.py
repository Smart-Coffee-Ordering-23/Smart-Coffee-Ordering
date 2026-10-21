"""Generate every coffee-shop sound effect as a small WAV file.

Run once from the project folder:   python tools/generate_sounds.py

Only the Python standard library is used, so requirements.txt does not
change. All files are short (<= 1.5 s), mono, 44.1 kHz, 16-bit and are
written to assets/sounds/. The sound style is one consistent family:

    warm marimba notes + soft chimes + ceramic cup clinks + airy whooshes

Everything is seeded, so running the script twice produces the same files.
"""
import math
import random
import struct
import wave
from pathlib import Path

SR = 44100                                   # samples per second
OUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "sounds"
RNG = random.Random(7)                       # fixed seed = identical files


# ============================================================ tiny helpers
def _n(seconds):
    """How many samples fit into a duration."""
    return max(1, int(SR * seconds))


def silence(seconds):
    return [0.0] * _n(seconds)


def sine(freq, seconds, amp=1.0, decay=None):
    """Pure tone; decay (seconds) makes it fade out smoothly."""
    out = []
    for i in range(_n(seconds)):
        t = i / SR
        env = math.exp(-t / decay) if decay else 1.0
        out.append(amp * env * math.sin(2.0 * math.pi * freq * t))
    return out


def sweep(f0, f1, seconds, amp=1.0, decay=None):
    """Tone that glides from f0 to f1 - a playful 'bloop'."""
    out = []
    phase = 0.0
    total = _n(seconds)
    for i in range(total):
        freq = f0 + (f1 - f0) * (i / total)
        phase += 2.0 * math.pi * freq / SR
        env = math.exp(-(i / SR) / decay) if decay else 1.0
        out.append(amp * env * math.sin(phase))
    return out


def noise(seconds, amp=1.0):
    """Soft white noise (the base of every whoosh / pouring sound)."""
    return [RNG.uniform(-amp, amp) for _ in range(_n(seconds))]


def lowpass(data, cutoff):
    """Muffle the noise. cutoff = Hz number, or a list of Hz per sample."""
    out = []
    y = 0.0
    for i, x in enumerate(data):
        fc = cutoff[i] if isinstance(cutoff, (list, tuple)) else cutoff
        alpha = 1.0 - math.exp(-2.0 * math.pi * fc / SR)
        y += alpha * (x - y)
        out.append(y)
    return out


def highpass(data, cutoff):
    """Remove the deep rumble (keeps the airy part of a pour)."""
    lp = lowpass(data, cutoff)
    return [x - y for x, y in zip(data, lp)]


def fade(data, attack=0.004, release=0.04):
    """Short fade in/out so the sound never clicks or pops."""
    out = list(data)
    a, r = _n(attack), _n(release)
    for i in range(min(a, len(out))):
        out[i] *= i / a
    for i in range(min(r, len(out))):
        out[-1 - i] *= i / r
    return out


def mix(*tracks):
    """Play several sounds at the same time (padded to the longest)."""
    length = max(len(track) for track in tracks)
    out = [0.0] * length
    for track in tracks:
        for i, value in enumerate(track):
            out[i] += value
    return out


def at(track, start):
    """Start a sound after `start` seconds of silence."""
    return silence(start) + list(track)


def normalize(data, peak):
    """Scale the sound so its loudest point equals `peak` (never > 1)."""
    loudest = max((abs(v) for v in data), default=0.0)
    if loudest == 0.0:
        return list(data)
    return [v * peak / loudest for v in data]


# ==================================================== coffee-shop timbres
def marimba(freq, seconds, amp=1.0, decay=0.18):
    """Warm wooden bar - the friendly core sound of the whole app."""
    return mix(sine(freq, seconds, amp, decay),
               sine(freq * 4.0, seconds, amp * 0.15, decay * 0.35))


def clink(seconds=0.12, amp=0.5, f1=2100.0, f2=2900.0):
    """Ceramic cup touching a saucer - our 'coffee' signature."""
    return mix(sine(f1, seconds, amp, seconds / 3.0),
               sine(f2, seconds, amp * 0.6, seconds / 4.0))


def whoosh(seconds=0.30, f_start=600.0, f_end=3200.0, amp=1.0):
    """Airy swipe: noise whose brightness sweeps up (or down if reversed)."""
    raw = noise(seconds)
    total = len(raw)
    cutoff = [f_start + (f_end - f_start) * (i / total) for i in range(total)]
    shaped = lowpass(lowpass(raw, cutoff), cutoff)   # two passes = soft air
    env = [math.sin(math.pi * (i / total)) ** 1.5 for i in range(total)]
    return [shaped[i] * env[i] * amp for i in range(total)]


def bubble(amp=0.35, seconds=0.06):
    """One small brewing bubble."""
    return sweep(240.0, 520.0, seconds, amp=amp, decay=0.03)


# ================================================================ writing
def write_wav(name, data, peak=0.5):
    """Fade, normalize and save one mono 16-bit WAV file."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = fade(normalize(data, peak))
    path = OUT_DIR / f"{name}.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        frames = bytearray()
        for value in data:
            value = max(-1.0, min(1.0, value))
            frames += struct.pack("<h", int(value * 32767))
        wav.writeframes(bytes(frames))
    print(f"  {name:<10} {len(data) / SR:5.2f}s  {path.stat().st_size // 1024:>3} KB")


# ============================================================ sound designs
def build_welcome():
    """Warm ascending chime + soft pad - stepping into a coffee shop."""
    notes = [(523.25, 0.00), (659.25, 0.13), (783.99, 0.26), (1046.50, 0.40)]
    melody = [at(marimba(freq, 0.75, 0.5, decay=0.22), start)
              for freq, start in notes]
    pad = lowpass(mix(sine(261.63, 1.2, 0.10), sine(392.00, 1.2, 0.07)), 900)
    return mix(*melody, fade(pad, attack=0.25, release=0.55))


def build_select():
    """Playful 'bloop' + tiny clink - a coffee card was picked."""
    pop = sweep(420.0, 780.0, 0.09, amp=0.7, decay=0.05)
    tick = lowpass(noise(0.015), 2600)
    return mix(pop, tick, at(clink(0.10, 0.35), 0.10))


def build_add_cart():
    """Cup on saucer + rising chime - satisfying 'added' confirmation."""
    cup = mix(clink(0.14, 0.5, 1950.0, 2600.0), lowpass(noise(0.012), 2400))
    chime = mix(at(marimba(783.99, 0.30, 0.4, 0.12), 0.12),
                at(marimba(1046.50, 0.35, 0.4, 0.15), 0.24))
    return mix(cup, chime)


def build_qty_up():
    """Very short soft tick, slightly high - one more cup."""
    return mix(sine(1150.0, 0.07, 0.6, decay=0.04),
               lowpass(noise(0.008), 3000))


def build_qty_down():
    """Same tick, lower - one cup less (so the two are distinguishable)."""
    return mix(sine(880.0, 0.07, 0.6, decay=0.04),
               lowpass(noise(0.008), 2600))


def build_swipe():
    """Smooth whoosh rising - moving forward between items/screens."""
    return whoosh(0.30, 600.0, 3200.0, amp=1.0)


def build_back():
    """Reverse whoosh falling - a soft 'undo' feeling."""
    return whoosh(0.26, 3000.0, 700.0, amp=0.9)


def build_gesture():
    """Soft modern blip for ordinary navigation taps."""
    return mix(sweep(620.0, 700.0, 0.11, amp=0.6, decay=0.05),
               sine(220.0, 0.07, 0.2, decay=0.035))


def build_smile():
    """Cheerful rising sparkle - the fun 10%-OFF moment."""
    notes = [(659.25, 0.00), (783.99, 0.10), (1046.50, 0.20), (1318.51, 0.30)]
    melody = [at(marimba(freq, 0.45, 0.45, 0.16), start)
              for freq, start in notes]
    sparkle = at(sine(2093.0, 0.25, 0.25, decay=0.08), 0.44)
    return mix(*melody, sparkle)


def build_confirm():
    """Classic two-note confirmation ding (kept for compatibility)."""
    return mix(marimba(783.99, 0.30, 0.5, 0.13),
               at(marimba(1046.50, 0.35, 0.5, 0.16), 0.12))


def build_success():
    """Short professional celebration: pickup notes resolve into a warm chord."""
    pickup = mix(sine(392.00, 0.10, 0.3, decay=0.06),
                 at(sine(440.00, 0.10, 0.3, decay=0.06), 0.09))
    chord = mix(sine(523.25, 0.85, 0.40, decay=0.32),
                sine(659.25, 0.85, 0.32, decay=0.32),
                sine(783.99, 0.85, 0.26, decay=0.32),
                sine(261.63, 0.85, 0.25, decay=0.38))
    cup = at(clink(0.12, 0.25), 0.18)           # one coffee-shop accent
    return mix(pickup, at(chord, 0.18), cup)


def build_sent():
    """Ticket tick + rising chime - the order flies to the barista."""
    ticket = lowpass(noise(0.03), 1800)
    tail = at(whoosh(0.26, 2600.0, 900.0, amp=0.6), 0.05)
    chime = mix(at(sine(659.25, 0.25, 0.4, decay=0.12), 0.08),
                at(sine(880.00, 0.30, 0.4, decay=0.14), 0.20))
    return mix(ticket, tail, chime)


def build_brew():
    """Short pour with soft bubbles and a final cup clink (max ~1.3 s)."""
    duration = 1.35
    raw = noise(duration)
    total = len(raw)
    cutoff = [1400.0 + 700.0 * math.sin(2.0 * math.pi * 2.5 * (i / total))
              for i in range(total)]
    filtered = highpass(lowpass(raw, cutoff), 500.0)
    env = []
    for i in range(total):
        p = i / total
        base = min(1.0, p / 0.15) * (1.0 - max(0.0, (p - 0.75) / 0.25))
        wobble = 0.85 + 0.15 * math.sin(2.0 * math.pi * 4.0 * p)
        env.append(max(0.0, base * wobble))
    pour = [filtered[i] * env[i] for i in range(total)]
    bubbles = mix(at(bubble(), 0.35), at(bubble(), 0.62), at(bubble(0.28), 0.95))
    done = at(clink(0.12, 0.35, 1900.0, 2500.0), 1.15)
    return mix(pour, bubbles, done)


def build_complete():
    """Order-up bell: two warm notes, friendly but not childish."""
    return mix(sine(1318.51, 0.40, 0.5, decay=0.16),
               at(sine(1046.50, 0.55, 0.5, decay=0.22), 0.16),
               sine(2637.00, 0.15, 0.12, decay=0.05))


def build_error():
    """Soft friendly 'cannot do that' - two gentle falling notes, no beep."""
    return mix(sine(392.00, 0.18, 0.5, decay=0.10),
               at(sine(311.13, 0.22, 0.5, decay=0.12), 0.14))


def build_empty():
    """Barely-there muted tap - the cart has nothing in it."""
    return mix(sine(320.0, 0.12, 0.5, decay=0.05),
               lowpass(noise(0.015), 1200))


# name -> (builder, peak volume)  (the peaks keep the whole set gentle)
SOUNDS = [
    ("welcome", build_welcome, 0.55),
    ("select", build_select, 0.50),
    ("add_cart", build_add_cart, 0.50),
    ("qty_up", build_qty_up, 0.30),
    ("qty_down", build_qty_down, 0.30),
    ("swipe", build_swipe, 0.40),
    ("back", build_back, 0.35),
    ("gesture", build_gesture, 0.32),
    ("smile", build_smile, 0.50),
    ("confirm", build_confirm, 0.45),
    ("success", build_success, 0.55),
    ("sent", build_sent, 0.45),
    ("brew", build_brew, 0.40),
    ("complete", build_complete, 0.50),
    ("error", build_error, 0.40),
    ("empty", build_empty, 0.22),
]


def main():
    print(f"Writing {len(SOUNDS)} sounds to {OUT_DIR}")
    for name, builder, peak in SOUNDS:
        write_wav(name, builder(), peak)
    print("Done.")


if __name__ == "__main__":
    main()
