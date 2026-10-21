"""AudioManager - realistic sound feedback for important actions.

Sound files live in assets/sounds/ (see assets/sounds/CREDITS.md for the
source and license of every recording):

    coffee_beans.wav      a coffee card was selected     ("select")
    gesture_detected.wav  a navigation gesture           ("gesture")
    add_to_cart.wav       a coffee was added to cart     ("add_cart")
    cup_place.wav         the cup (quantity) screen opens ("cup")
    coffee_pouring.wav    order sent - pouring starts    ("sent")
    coffee_brewing.wav    brewing animation              ("brew")
    order_success.wav     order confirmed / finished     ("success"/"complete")
    cancel.wav            order or selection cancelled   ("cancel")
    discount.wav          the smile discount activates   ("smile")
    cafe_ambience.wav     OPTIONAL background noise      ("ambience")

Legacy UI sounds (swipe, back, qty_up, qty_down, empty, error, welcome)
keep their previous files.

Rules:
* every WAV is loaded ONCE at startup and reused (pygame.mixer.Sound),
* sounds never re-trigger within config.SOUND_RETRIGGER_SECONDS,
* never more than config.SOUND_MAX_VOICES sounds at once,
* ambience is OPTIONAL and disabled by default,
* if pygame's mixer or a sound file is missing, the application keeps
  running silently - sound is only a nice extra, never a requirement.
"""
import time
from pathlib import Path

import pygame

from src import config

# event name -> file name in assets/sounds/
SOUND_FILES = {
    # realistic coffee-shop recordings (this upgrade)
    "select": "coffee_beans.wav",
    "gesture": "gesture_detected.wav",
    "add_cart": "add_to_cart.wav",
    "cup": "cup_place.wav",
    "sent": "coffee_pouring.wav",
    "brew": "coffee_brewing.wav",
    "success": "order_success.wav",
    "complete": "order_success.wav",   # same file as success - loaded once!
    "cancel": "cancel.wav",
    "smile": "discount.wav",
    "ambience": "cafe_ambience.wav",
    # new lively sounds (made by tools/generate_fx_sounds.py)
    "hover": "fx_hover.wav",
    "music": "fx_music.wav",
    "confetti": "fx_confetti.wav",
    # legacy UI sounds kept from the previous version
    "back": "back.wav",
    "swipe": "swipe.wav",
    "qty_up": "qty_up.wav",
    "qty_down": "qty_down.wav",
    "empty": "empty.wav",
    "error": "error.wav",
    "welcome": "welcome.wav",
}

# One signature jingle per coffee (drink_1 ... drink_12), a musical note per cup
# count (qty_1 ... qty_10) and three music "scenes" that change with the screen.
for _i in range(1, 13):
    SOUND_FILES[f"drink_{_i}"] = f"fx_drink_{_i}.wav"
for _i in range(1, 11):
    SOUND_FILES[f"qty_{_i}"] = f"fx_qty_{_i}.wav"
SOUND_FILES["music_welcome"] = "fx_music_welcome.wav"
SOUND_FILES["music_party"] = "fx_music_party.wav"
MUSIC_NAMES = ("music", "music_welcome", "music_party")
SCENE_TO_MUSIC = {"welcome": "music_welcome", "menu": "music", "party": "music_party"}
DRINK_JINGLES = 12


def find_sound_file(file_name):
    """Path of a sound file. Also accepts browser copies like 'fx_music (1).wav'."""
    path = config.SOUNDS_DIR / file_name
    if path.exists():
        return path
    for copy in sorted(config.SOUNDS_DIR.glob(f"{Path(file_name).stem} (*).wav")):
        return copy
    return None


# If a realistic file is missing, fall back to the older placeholder so
# the event still makes a sound. coffee_beans.wav is still pending a
# manual download (see assets/sounds/CREDITS.md).
SOUND_FALLBACK_FILES = {
    "select": ("select.wav",),
}


class AudioManager:
    """Loads the optional sound effects once and plays them safely."""

    def __init__(self):
        self.enabled = config.SOUND_ENABLED
        self.volume = max(0.0, min(1.0, config.SOUND_VOLUME))
        self.mixer_ready = False
        self.sounds = {}             # event name -> pygame.mixer.Sound (once)
        self.error_message = ""
        self._scheduled = []         # list of [due_time, name]
        self._last_played = {}       # name -> monotonic time of last start
        self._channels = []          # voices currently used (max-voices rule)
        self._ambience_channel = None
        self._music_channel = None
        self._music_name = None
        self._duck = 1.0                 # music gets quieter while an effect plays
        self._duck_until = 0.0
        if self.enabled:
            self._init_mixer()
            self._load_sounds()

    # ============================================================ setup
    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.mixer_ready = True
        except pygame.error as error:
            self.error_message = f"Sound disabled: {error}"
            self.mixer_ready = False
            print(f"[AudioManager] {self.error_message}")

    def _load_sounds(self):
        """Load every WAV exactly ONCE; several events may share one file."""
        if not self.mixer_ready:
            return
        loaded_by_file = {}          # file name -> Sound (no double loading)
        for name, file_name in SOUND_FILES.items():
            # a generated "fx_<event>.wav" (livelier set) is preferred when it exists
            candidates = [f"fx_{name}.wav", file_name] + list(SOUND_FALLBACK_FILES.get(name, ()))
            for candidate in candidates:
                path = find_sound_file(candidate)
                if path is None:
                    continue        # missing sound files are fine - stay silent
                try:
                    if candidate not in loaded_by_file:
                        loaded_by_file[candidate] = pygame.mixer.Sound(str(path))
                    sound = loaded_by_file[candidate]
                    sound.set_volume(1.0 if name in MUSIC_NAMES else self.volume)
                    self.sounds[name] = sound
                    break           # primary file preferred over fallback
                except pygame.error as error:
                    print(f"[AudioManager] Could not load {candidate}: {error}")
                    continue        # try the next candidate file

    @property
    def is_ready(self):
        return self.mixer_ready and bool(self.sounds)

    # ============================================================ controls
    def set_enabled(self, enabled):
        """Mute/unmute at runtime (the M key). Muting also clears the queue."""
        enabled = bool(enabled)
        if enabled and not self.mixer_ready:
            self._init_mixer()       # app started silent - wake the mixer up
            self._load_sounds()
        if not enabled:
            self._scheduled = []      # mute cancels every scheduled sound
            self.stop_ambience()
            self.stop_music()
            if self.mixer_ready:
                try:
                    pygame.mixer.stop()   # and cuts short what is playing
                except pygame.error:
                    pass
        self.enabled = enabled
        if enabled and config.SOUND_MUSIC_ENABLED:
            self.start_music()

    def set_volume(self, volume):
        """Master volume 0.0 - 1.0 (clamped); applies to loaded sounds."""
        self.volume = max(0.0, min(1.0, float(volume)))
        for name, sound in self.sounds.items():
            sound.set_volume(1.0 if name in MUSIC_NAMES else self.volume)
        if self._ambience_channel is not None:
            self._ambience_channel.set_volume(self._ambience_volume())
        self._apply_music_volume()

    def _ambience_volume(self):
        """Ambience stays quietly in the background."""
        return self.volume * config.SOUND_AMBIENCE_VOLUME

    # ============================================================ playback
    def _voices_in_use(self):
        self._channels = [channel for channel in self._channels if channel.get_busy()]
        return len(self._channels)

    def play(self, name, force=False):
        """Play one of the known sounds. Never raises.

        Returns True only when playback actually started. The same sound
        is blocked for config.SOUND_RETRIGGER_SECONDS (no per-frame spam)
        and never more than config.SOUND_MAX_VOICES sounds run together.
        """
        if not self.enabled or not self.mixer_ready:
            return False
        sound = self.sounds.get(name)
        if sound is None:
            return False
        now = time.monotonic()
        if not force and now - self._last_played.get(name, -10.0) < config.SOUND_RETRIGGER_SECONDS:
            return False            # anti-spam guard for rapid gestures
        if not force and self._voices_in_use() >= config.SOUND_MAX_VOICES:
            return False            # never overload the cafe with noise
        try:
            channel = sound.play()
            if channel is not None:
                self._channels.append(channel)
            self._last_played[name] = now
            if name not in MUSIC_NAMES:
                self._duck_until = now + 0.8       # music steps back so the effect is heard
            return True
        except pygame.error as error:
            print(f"[AudioManager] Could not play '{name}': {error}")
            return False

    def play_later(self, name, delay):
        """Schedule a sound `delay` seconds from now (order-brew sequence)."""
        if not self.enabled:
            return None
        due = time.monotonic() + max(0.0, delay)
        for entry in self._scheduled:          # ignore duplicate reminders
            if entry[1] == name:
                return None
        self._scheduled.append([due, name])

    def update(self):
        """Start every scheduled sound that is now due; returns their names.

        Call this once per frame from the main loop.
        """
        if not self.enabled:
            return []
        now = time.monotonic()
        self._duck += ((0.45 if now < self._duck_until else 1.0) - self._duck) * 0.15
        self._apply_music_volume()
        started = []
        remaining = []
        for due, name in self._scheduled:
            if due <= now:
                if self.play(name, force=True):
                    started.append(name)
            else:
                remaining.append([due, name])
        self._scheduled = remaining
        return started

    # ============================================================ ambience
    def start_ambience(self):
        """Loop the optional cafe background sound (disabled by default)."""
        if not self.enabled or not self.mixer_ready:
            return False
        if self._ambience_channel is not None and self._ambience_channel.get_busy():
            return True             # already running
        sound = self.sounds.get("ambience")
        if sound is None:
            return False            # file not provided - perfectly fine
        try:
            self._ambience_channel = sound.play(loops=-1)   # loop forever
            if self._ambience_channel is not None:
                self._ambience_channel.set_volume(self._ambience_volume())
            return self._ambience_channel is not None
        except pygame.error as error:
            print(f"[AudioManager] Could not start ambience: {error}")
            return False

    def stop_ambience(self):
        """Stop the background cafe sound."""
        if self._ambience_channel is not None:
            try:
                self._ambience_channel.stop()
            except pygame.error:
                pass
            self._ambience_channel = None

    # ============================================================ music
    def _music_volume(self):
        return self.volume * config.SOUND_MUSIC_VOLUME * self._duck

    def _apply_music_volume(self):
        if self._music_channel is not None:
            try:
                self._music_channel.set_volume(self._music_volume())
            except pygame.error:
                pass

    def start_music(self, scene="welcome"):
        """Start the looping cafe music right away. Silent if no music file exists."""
        return self.set_music_scene(scene)

    def set_music_scene(self, scene):
        """Switch the music to the scene's track with a smooth cross-fade.

        scene: "welcome" (bright intro), "menu" (calm lo-fi), "party" (celebration).
        Calling it every frame is fine - nothing happens while the scene is unchanged.
        """
        if not self.enabled or not self.mixer_ready:
            return False
        name = SCENE_TO_MUSIC.get(scene, "music")
        if name not in self.sounds:
            name = "music"                     # missing scene file -> the main loop
        if name not in self.sounds:
            return False
        if (name == self._music_name and self._music_channel is not None
                and self._music_channel.get_busy()):
            return True
        try:
            if self._music_channel is not None:
                self._music_channel.fadeout(700)
            self._music_channel = self.sounds[name].play(loops=-1, fade_ms=700)
            self._music_name = name
            self._apply_music_volume()
            return self._music_channel is not None
        except pygame.error as error:
            print(f"[AudioManager] Could not start music: {error}")
            return False

    def stop_music(self):
        if self._music_channel is not None:
            try:
                self._music_channel.stop()
            except pygame.error:
                pass
            self._music_channel = None
            self._music_name = None

    # ============================================================ musical feedback
    def play_drink(self, product_id):
        """Each coffee has its own little jingle. False if the file is missing."""
        number = (int(product_id) - 1) % DRINK_JINGLES + 1
        return self.play(f"drink_{number}", force=True)

    def play_quantity(self, quantity):
        """One more cup = the next note of a happy scale (1 -> low, 10 -> high)."""
        number = max(1, min(10, int(quantity)))
        return self.play(f"qty_{number}", force=True)
