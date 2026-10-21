"""Smart Coffee Ordering - application entry point.

Run from the project folder:      python main.py

Flow:
    Camera -> Hand/Face Tracking -> Gesture Engine -> Interaction Controller
        -> Menu -> Cart -> Order Manager -> Kitchen Queue -> Done

Keyboard and mouse always work, even when no camera is available.
"""
import time

import pygame

from src import config
from src.audio_manager import AudioManager
from src.camera import Camera
from src.cart import Cart
from src.gesture_engine import GestureEngine
from src.hand_tracker import FaceTracker, HandTracker
from src.interaction_controller import InteractionController
from src.kitchen_queue import KitchenQueue
from src.menu_manager import MenuManager
from src.order_manager import OrderManager, format_order_number
from src.renderer import MAIN_WIDTH, WINDOW_SIZE, Renderer

KEY_TO_EVENT = {
    pygame.K_o: "OPEN_PALM",
    pygame.K_p: "POINTING",
    pygame.K_LEFT: "SWIPE_LEFT",
    pygame.K_RIGHT: "SWIPE_RIGHT",
    pygame.K_2: "TWO_FINGERS",
    pygame.K_t: "THUMBS_UP",
    pygame.K_f: "FIST",
    pygame.K_b: "BLINK",
    pygame.K_g: "SMILE",
}

KEY_TO_SCREEN = {
    pygame.K_F1: config.WELCOME,
    pygame.K_F2: config.MENU,
    pygame.K_F3: config.SELECT,
    pygame.K_F4: config.QUANTITY,
    pygame.K_F5: config.DISCOUNT,
    pygame.K_F6: config.CONFIRM,
    pygame.K_F7: config.SUMMARY,
    pygame.K_F8: config.COMPLETE,
}
SECTION_LABELS = dict(config.STEP_LABELS)


def clamp(value, low=0.0, high=1.0):
    """Keep a number inside the range [low, high] (used for the pointer)."""
    return max(low, min(high, value))


class CoffeeApp:
    """Connects camera, AI, gestures, menu, cart, orders and the UI."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        flags = pygame.SCALED | pygame.RESIZABLE
        if config.START_FULLSCREEN:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(WINDOW_SIZE, flags)
        pygame.mouse.set_visible(not config.GESTURE_ONLY)
        self.clock = pygame.time.Clock()
        self.running = True

        self.menu = MenuManager()
        self.cart = Cart()
        self.order_manager = OrderManager()
        self.audio = AudioManager()
        if config.SOUND_AMBIENCE_ENABLED:
            self.audio.start_ambience()   # optional cafe background noise
        self.kitchen = KitchenQueue(self.order_manager)
        self.controller = InteractionController(
            self.menu, self.cart, self.order_manager, self.kitchen, self.audio)
        self.renderer = Renderer(self.screen, self.menu)

        self.camera = Camera()
        self.hand_tracker = HandTracker()
        self.face_tracker = FaceTracker()
        self.engine = GestureEngine()

        self.frame = None
        self.hand_landmarks = None
        self.face_info = None
        self.pointer = None
        self.pointer_from_hand = False

        if self.menu.error_message:
            self.controller.set_message(self.menu.error_message)
        elif not self.camera.is_connected:
            self.controller.set_message("Camera not available - use the keyboard")

    def run(self):
        while self.running:
            events = self.read_input_events() + self.read_vision_events()
            self.update_pointer()
            self.update_hover_context()
            for event in events:
                handled = self.controller.handle_event(event)
                if handled is False:
                    self.engine.rearm()      # allow the gesture to try again
            self.kitchen.update()
            self.handle_kitchen_events()
            self.controller.update()
            self.draw()
            self.clock.tick(config.FPS)

    def close(self):
        self.camera.release()
        self.hand_tracker.close()
        self.face_tracker.close()
        self.order_manager.close()
        pygame.quit()

    def read_input_events(self):
        """Keyboard, mouse and window events -> gesture events / actions."""
        events = []
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                self.running = False
            elif pygame_event.type == pygame.KEYDOWN and config.GESTURE_ONLY:
                if pygame_event.key == pygame.K_q:      # operator exit only
                    self.running = False
            elif pygame_event.type == pygame.KEYDOWN:
                key = pygame_event.key
                if key == pygame.K_ESCAPE:
                    if self.controller.screen in (config.WELCOME, config.COMPLETE):
                        self.running = False
                    else:
                        events.append("BLINK")
                elif key == pygame.K_q:
                    self.running = False
                elif key == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except pygame.error:
                        self.controller.set_message("Fullscreen is not supported here")
                elif key in KEY_TO_SCREEN:
                    self.controller.go_to_screen(KEY_TO_SCREEN[key])
                elif key == pygame.K_RETURN:
                    # Enter = point at the first coffee, or confirm a screen.
                    target = ("POINTING" if self.controller.screen == config.MENU
                              else "THUMBS_UP")
                    events.append(target)
                elif key == pygame.K_s:
                    self.controller.go_to_screen(config.SUMMARY)
                elif key == pygame.K_c:
                    self.controller.clear_cart()
                elif key in KEY_TO_EVENT:
                    events.append(KEY_TO_EVENT[key])
            elif (pygame_event.type == pygame.MOUSEBUTTONDOWN and pygame_event.button == 1
                  and not config.GESTURE_ONLY):
                self.handle_click(pygame_event.pos)
        return events

    def handle_click(self, position):
        """A mouse click runs the button or card under the cursor."""
        hit = self.renderer.action_at(position)
        if hit is None:
            return
        action, value = hit
        self.controller.perform(action, value)

    def read_vision_events(self):
        """Read the camera and turn hand/face data into gesture events."""
        events = []
        self.frame = self.camera.read_frame()
        if self.frame is None:
            self.hand_landmarks = None
            self.face_info = None
            return events
        self.hand_landmarks = self.hand_tracker.find_hand(self.frame)
        self.face_info = self.face_tracker.detect(self.frame)
        events.extend(self.engine.update(self.hand_landmarks, self.face_info))
        return events

    def update_pointer(self):
        """The pointer follows the index fingertip, or the mouse without a hand."""
        if self.hand_landmarks:
            tip_x, tip_y = self.hand_landmarks[8]
            target = (clamp((tip_x - 0.15) / 0.70) * MAIN_WIDTH,
                      clamp((tip_y - 0.10) / 0.65) * config.WINDOW_HEIGHT)
            if self.pointer is None or not self.pointer_from_hand:
                self.pointer = target
            else:
                # Smooth the movement so the pointer does not jump around.
                self.pointer = (self.pointer[0] * 0.65 + target[0] * 0.35,
                                self.pointer[1] * 0.65 + target[1] * 0.35)
            self.pointer_from_hand = True
        else:
            mouse = None if config.GESTURE_ONLY else pygame.mouse.get_pos()
            self.pointer = mouse if mouse and mouse[0] < MAIN_WIDTH else None
            self.pointer_from_hand = False

    def update_hover_context(self):
        """Tell the controller which coffee card / step the pointer is on."""
        hit = self.renderer.action_at(self.pointer)
        if hit is not None and hit[0] == "card":
            self.controller.hovered_product = hit[1]
        else:
            self.controller.hovered_product = None
        if hit is not None and hit[0] == "step":
            self.controller.hovered_step = hit[1]
        else:
            self.controller.hovered_step = None

    def handle_kitchen_events(self):
        """Play the success sound when the kitchen finishes an order."""
        for order_id in self.kitchen.pop_completed_events():
            self.audio.play("complete")
            self.controller.set_message(f"Order {format_order_number(order_id)} is ready!")

    def draw(self):
        """Draw one frame: navbar, progress rail, screen, bars and feedback."""
        r = self.renderer
        ctrl = self.controller
        ai_ready = self.camera.is_connected
        selected = self.menu.selected_product

        r.draw_background()
        section = SECTION_LABELS.get(ctrl.screen, "Menu")
        r.draw_navbar(section, self.cart.total_quantity(), ai_ready)
        r.draw_progress(ctrl.screen, ctrl.hovered_step)

        if ctrl.screen == config.WELCOME:
            r.draw_welcome(ai_ready)
        elif ctrl.screen == config.MENU:
            r.draw_menu(ctrl.hovered_product, selected)
        elif ctrl.screen == config.SELECT:
            r.draw_select(selected)
        elif ctrl.screen == config.QUANTITY:
            r.draw_quantity(selected, ctrl.quantity)
        elif ctrl.screen == config.DISCOUNT:
            r.draw_discount(self.cart)
        elif ctrl.screen == config.CONFIRM:
            r.draw_confirm(self.cart)
        elif ctrl.screen == config.SUMMARY:
            r.draw_summary(self.cart, ctrl.order_number(),
                           self.kitchen.get_status(ctrl.order_id))
        elif ctrl.screen == config.COMPLETE:
            seconds_left = config.COMPLETE_SECONDS - (time.time() - ctrl.complete_started_at)
            r.draw_complete(self.cart, ctrl.order_number(),
                            self.kitchen.get_status(ctrl.order_id), seconds_left)

        r.draw_instruction_bar()
        r.draw_sidebar(self.frame, self.hand_landmarks, self.build_debug_rows(),
                       self.engine.progress, ai_ready,
                       self.hand_landmarks is not None, self.camera_status_message())
        r.draw_toast(ctrl.active_message)

        pointer_progress = (self.engine.progress
                            if self.pointer_from_hand and self.engine.stable_gesture == "POINTING"
                            else 0.0)
        if self.pointer is not None and ctrl.screen != config.WELCOME:
            r.draw_pointer(self.pointer, pointer_progress)
        pygame.display.flip()

    def camera_status_message(self):
        """Short status line shown in the camera panel of the sidebar."""
        if not self.camera.is_connected:
            return "Camera unavailable - keyboard mode"
        if self.hand_landmarks is not None:
            return "Hand detected"
        return "Show your hand to begin"

    def build_debug_rows(self):
        """Technical rows for the camera panel - only drawn in DEBUG_MODE."""
        face = self.face_info
        face_found = face is not None and face.face_found
        hand_found = self.hand_landmarks is not None
        camera_ok = self.camera.is_connected
        gesture = self.engine.stable_gesture

        smiling = (
            face.is_smiling
            if face is not None and face.face_found
            else False
        )
        smile_ratio = (
            f"{face.smile_ratio:.2f}"
            if face is not None and face.face_found
            else "-"
        )

        return [
            ("Camera", "Connected" if camera_ok else "Not found", camera_ok),
            ("Hand", "Detected" if hand_found else "Not detected", hand_found),
            (
                "Landmarks",
                len(self.hand_landmarks) if self.hand_landmarks is not None else 0,
                hand_found,
            ),
            ("Gesture", gesture.replace("_", " ").title(), gesture != "NONE"),
            ("Face", "Detected" if face_found else "Not detected", face_found),
            ("Smiling", "Yes" if smiling else "No", smiling),
            ("Smile ratio", smile_ratio, face_found),
        ]


def main():
    app = CoffeeApp()
    try:
        app.run()
    finally:
        app.close()


if __name__ == "__main__":
    main()