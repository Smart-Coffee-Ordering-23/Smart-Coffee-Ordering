"""Tests for the coffee-shop sound system.

The controller tests use a FakeAudio that only records sound names, so
they never need an audio device. The AudioManager tests use SDL's dummy
audio driver, so they also work on machines without sound.
"""
import time

import pygame

from src import config
from src.audio_manager import SOUND_FILES, AudioManager
from src.cart import Cart
from src.interaction_controller import InteractionController
from src.kitchen_queue import KitchenQueue
from src.menu_manager import MenuManager


class FakeAudio:
    """Records which sounds the controller would play (no real audio)."""

    def __init__(self):
        self.played = []
        self.scheduled = []

    def play(self, name):
        self.played.append(name)
        return True

    def play_later(self, name, delay):
        self.scheduled.append((name, delay))


class FakeOrders:
    """OrderManager stand-in so the tests never touch the real database."""

    error_message = ""

    def create_order(self, cart):
        return 1


def make_controller():
    audio = FakeAudio()
    controller = InteractionController(MenuManager(), Cart(), FakeOrders(),
                                       KitchenQueue(), audio)
    return controller, audio


def make_audio_manager(monkeypatch):
    """A real AudioManager on SDL's silent dummy audio device."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.quit()              # force a fresh init with the dummy driver
    return AudioManager()


# ============================================================ sound files
def test_every_sound_file_exists():
    """All mapped sound files must be present in assets/sounds/."""
    for file_name in SOUND_FILES.values():
        assert (config.SOUNDS_DIR / file_name).exists(), file_name


def test_audio_manager_loads_all_sounds(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    assert set(audio.sounds) == set(SOUND_FILES)
    assert audio.is_ready


def test_missing_or_disabled_sound_never_raises(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    assert audio.play("does_not_exist") is False   # unknown name -> silent
    audio.set_enabled(False)
    assert audio.play("select") is False           # muted -> silent
    assert audio.play_later("sent", 0.1) is None   # muted -> nothing scheduled
    assert audio.update() == []
    audio.set_enabled(True)
    assert audio.play("select") is True


def test_same_sound_is_not_retriggered_every_frame(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    assert audio.play("select") is True
    assert audio.play("select") is False           # cooldown blocks the spam
    assert audio.play("select") is False


def test_scheduled_sounds_play_after_their_delay(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    audio.play_later("sent", 0.05)
    audio.play_later("sent", 0.05)                 # duplicate is ignored
    assert audio.update() == []                    # not due yet
    # Poll instead of a single sleep: Windows can wake from time.sleep()
    # a few milliseconds early, which would make a fixed sleep flaky.
    deadline = time.monotonic() + 2.0
    started = []
    while time.monotonic() < deadline and not started:
        started = audio.update()
        time.sleep(0.01)
    assert started == ["sent"]
    assert audio.update() == []                    # queue is empty now


def test_volume_is_clamped_between_zero_and_one(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    audio.set_volume(5.0)
    assert audio.volume == 1.0
    audio.set_volume(-1.0)
    assert audio.volume == 0.0


def test_mute_cancels_scheduled_sounds(monkeypatch):
    audio = make_audio_manager(monkeypatch)
    audio.play_later("brew", 0.01)
    audio.set_enabled(False)                       # cancels the queue too
    time.sleep(0.02)
    assert audio.update() == []


def test_sounds_can_be_switched_on_at_runtime(monkeypatch):
    """App started with SOUND_ENABLED = False -> pressing M starts the mixer."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr(config, "SOUND_ENABLED", False)
    pygame.mixer.quit()
    audio = AudioManager()
    assert audio.mixer_ready is False              # started silently
    assert not audio.sounds
    audio.set_enabled(True)                        # the M key
    assert audio.mixer_ready and audio.sounds
    assert audio.play("welcome") is True


# ================================================= controller sound mapping
def test_selecting_a_coffee_plays_select():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    assert audio.played == ["select"]
    assert controller.cart.is_empty()              # selecting adds nothing yet


def test_add_to_cart_plays_add_cart():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    controller.screen = config.QUANTITY
    assert controller._add_selected_to_cart() is True
    assert "add_cart" in audio.played
    assert not controller.cart.is_empty()


def test_quantity_buttons_play_soft_ticks():
    controller, audio = make_controller()
    controller.perform("qty_plus")
    assert audio.played[-1] == "qty_up"
    controller.perform("qty_plus")
    controller.perform("qty_minus")
    assert audio.played[-1] == "qty_down"


def test_swipe_changes_pages_with_a_whoosh():
    controller, audio = make_controller()
    controller.screen = config.MENU
    controller.handle_event("SWIPE_RIGHT")
    assert "swipe" in audio.played


def test_swipe_at_the_end_of_the_flow_gives_a_soft_error():
    controller, audio = make_controller()
    controller.screen = config.WELCOME
    controller.handle_event("SWIPE_LEFT")           # nothing before Welcome
    assert audio.played[-1] == "error"
    assert controller.active_message                # the user is told why


def test_back_plays_reverse_whoosh_and_blocks_on_welcome():
    controller, audio = make_controller()
    controller.screen = config.SELECT
    controller.go_back()
    assert audio.played[-1] == "back"
    assert controller.screen == config.MENU
    controller.screen = config.WELCOME
    controller.go_back()
    assert audio.played[-1] == "error"


def test_smile_discount_is_the_fun_moment():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    controller._add_selected_to_cart()
    controller.screen = config.DISCOUNT
    controller.handle_event("SMILE")
    assert "smile" in audio.played
    assert controller.cart.discount_applied
    assert "Nice smile!" in controller.message
    assert "10% OFF" in controller.message
    assert "☕" in controller.message
    # a second smile: no new discount and no second sound
    played_before = list(audio.played)
    controller.handle_event("SMILE")
    assert audio.played == played_before
    assert "already applied" in controller.message


def test_successful_order_runs_success_sent_brew_sequence():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    controller._add_selected_to_cart()
    controller.screen = config.CONFIRM
    assert controller.confirm_order() is True
    assert audio.played[-1] == "success"
    names = [name for name, _ in audio.scheduled]
    delays = dict(audio.scheduled)
    assert names == ["sent", "brew"]                # never at the same time
    assert delays["brew"] > delays["sent"] > 0


def test_empty_cart_checkout_is_subtle_not_an_error():
    controller, audio = make_controller()
    controller.screen = config.CONFIRM
    assert controller.confirm_order() is False
    assert audio.played[-1] == "empty"
    assert controller.order_id is None


def test_new_order_goes_back_to_the_welcome_chime():
    controller, audio = make_controller()
    controller.start_new_order()
    assert audio.played[-1] == "welcome"


# ============================================ realistic-sound upgrade (this PR)
NEW_REALISTIC_FILES = [
    "coffee_brewing.wav", "coffee_pouring.wav", "cup_place.wav",
    "coffee_beans.wav", "gesture_detected.wav", "add_to_cart.wav",
    "order_success.wav", "cancel.wav", "discount.wav", "cafe_ambience.wav",
]


def test_all_ten_new_sound_files_exist():
    """Every file of the required structure must really be present."""
    for file_name in NEW_REALISTIC_FILES:
        assert (config.SOUNDS_DIR / file_name).exists(), file_name


def test_coffee_beans_file_added_once_download_succeeds():
    """coffee_beans.wav was downloaded from Wikimedia (see CREDITS.md)."""
    assert (config.SOUNDS_DIR / "coffee_beans.wav").exists()


def test_success_and_complete_share_one_loaded_sound(monkeypatch):
    """order_success.wav is loaded ONCE and reused for both events."""
    audio = make_audio_manager(monkeypatch)
    assert audio.sounds["success"] is audio.sounds["complete"]


def test_new_event_mapping_points_to_realistic_files():
    assert SOUND_FILES["gesture"] == "gesture_detected.wav"
    assert SOUND_FILES["add_cart"] == "add_to_cart.wav"
    assert SOUND_FILES["sent"] == "coffee_pouring.wav"
    assert SOUND_FILES["brew"] == "coffee_brewing.wav"
    assert SOUND_FILES["success"] == "order_success.wav"
    assert SOUND_FILES["cancel"] == "cancel.wav"
    assert SOUND_FILES["smile"] == "discount.wav"
    assert SOUND_FILES["select"] == "coffee_beans.wav"
    assert SOUND_FILES["cup"] == "cup_place.wav"


def test_ambience_is_disabled_by_default(monkeypatch):
    """Requirement: background cafe noise stays optional and OFF."""
    assert config.SOUND_AMBIENCE_ENABLED is False
    audio = make_audio_manager(monkeypatch)
    assert audio.start_ambience() in (True, False)   # never raises
    audio.stop_ambience()                            # never raises


def test_cancel_actions_play_the_cancel_sound():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    controller.screen = config.QUANTITY
    controller.cancel()                              # FIST gesture
    assert audio.played[-1] == "cancel"


def test_going_to_the_quantity_screen_plays_cup_place():
    controller, audio = make_controller()
    controller.select_product(controller.menu.products[0])
    controller.screen = config.SELECT
    controller.handle_event("THUMBS_UP")             # cup on the scale
    assert audio.played[-1] == "cup"
    assert controller.screen == config.QUANTITY
