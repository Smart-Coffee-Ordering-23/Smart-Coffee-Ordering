"""InteractionController - connects recognized gestures to application actions.

    Gesture  ->  InteractionController  ->  application action

Example: the event "POINTING" selects the coffee card under the finger.

This file contains NO drawing code and NO SQL - the database work is
delegated to OrderManager. Its main job is translating recognized
gestures (and mouse/keyboard commands) into application actions.
"""
import time

from src import config
from src.order_manager import format_order_number


class InteractionController:
    """Holds the current screen and applies every action of the order flow."""

    # Where the BLINK ("go back") event leads from each screen
    BACK_SCREEN = {
        config.MENU: config.WELCOME,
        config.SELECT: config.MENU,
        config.QUANTITY: config.SELECT,
        config.DISCOUNT: config.QUANTITY,
        config.CONFIRM: config.DISCOUNT,
    }

    def __init__(self, menu_manager, cart, order_manager, kitchen_queue, audio=None, clock=None):
        self.menu = menu_manager
        self.cart = cart
        self.order_manager = order_manager
        self.kitchen = kitchen_queue
        self.audio = audio
        self._clock = clock or time.time

        # current state of the flow
        self.screen = config.WELCOME
        self.quantity = 1
        self.order_id = None
        self.message = ""
        self.message_until = 0.0
        self.complete_started_at = 0.0

        # what the user is pointing at (updated by main.py every frame)
        self.hovered_product = None
        self.hovered_step = None

    # ============================================================ helpers
    def set_message(self, text):
        self.message = text
        self.message_until = self._clock() + config.MESSAGE_SECONDS

    @property
    def active_message(self):
        """The toast text while it is still fresh, else an empty string."""
        return self.message if self._clock() < self.message_until else ""

    def order_number(self):
        """'#001' for the saved order, or None before an order exists."""
        if self.order_id is None:
            return None
        return format_order_number(self.order_id)

    def _sound(self, name):
        if self.audio is not None:
            self.audio.play(name)

    def _play_later(self, name, delay):
        """Schedule a sound `delay` seconds from now (order success sequence)."""
        if self.audio is not None and hasattr(self.audio, "play_later"):
            self.audio.play_later(name, delay)

    # ============================================================ dispatch
    def handle_event(self, event):
        """Apply one gesture/keyboard event.

        Returns False only when the action failed and the gesture should
        be allowed to try again (the engine is then re-armed by main.py).
        """
        # Pointing at the step rail at the top jumps straight to that screen
        if event == "POINTING" and self.hovered_step is not None:
            if self.hovered_step != self.screen:
                self.go_to_screen(self.hovered_step)
                self._sound("gesture")
            return True
        # Swiping moves between screens (Menu and Quantity use swipes first)
        if event in ("SWIPE_LEFT", "SWIPE_RIGHT") and self.screen not in (config.MENU, config.QUANTITY):
            self._swipe_between_screens(event)
            return True
        if event == "BLINK":
            self.go_back()
            return True
        if event == "FIST":
            self.cancel()
            return True
        if event == "SMILE":
            self._apply_smile_discount()
            return True

        handler = {
            config.WELCOME: self._on_welcome,
            config.MENU: self._on_menu,
            config.SELECT: self._on_select,
            config.QUANTITY: self._on_quantity,
            config.DISCOUNT: self._on_discount,
            config.CONFIRM: self._on_confirm,
            config.SUMMARY: self._on_summary,
            config.COMPLETE: self._on_complete,
        }[self.screen]
        return handler(event)

    # ============================================================ screens
    def _on_welcome(self, event):
        if event == "OPEN_PALM":
            self.screen = config.MENU
            self._sound("gesture")
            self.set_message("Menu opened - point at a coffee")
        return True

    def _on_menu(self, event):
        if event == "SWIPE_RIGHT":
            if self.menu.next_page():
                self._sound("swipe")        # whoosh: next page of coffees
            else:
                self._swipe_between_screens(event)
        elif event == "SWIPE_LEFT":
            if self.menu.previous_page():
                self._sound("swipe")        # whoosh: previous page of coffees
            else:
                self._swipe_between_screens(event)
        elif event == "POINTING":
            if self.hovered_product is None:
                self.set_message("Point your finger at a coffee card")
                self._sound("error")        # soft friendly hint, no harsh beep
                return False        # let POINTING try again
            self.select_product(self.hovered_product)
        elif event == "THUMBS_UP":
            if self.cart.is_empty():
                self.set_message("Point at a coffee first")
                self._sound("empty")        # subtle: nothing to check out yet
            else:
                self.go_to_screen(config.CONFIRM)
                self._sound("gesture")
        return True

    def _on_select(self, event):
        if event == "THUMBS_UP":
            self.screen = config.QUANTITY
            self._sound("cup")          # the cup is placed on the scale
        return True

    def _on_quantity(self, event):
        if event == "TWO_FINGERS":
            if self.quantity < config.MAX_QUANTITY:
                self.quantity += 1
                self._sound("qty_up")            # very short soft tick
            else:
                self.quantity = 1                 # wraps back to one cup
                self._sound("qty_down")
        elif event == "SWIPE_RIGHT":
            if self.quantity < config.MAX_QUANTITY:
                self.quantity += 1
                self._sound("qty_up")            # very short soft tick
            else:
                self._swipe_between_screens(event)   # already at the maximum
        elif event == "SWIPE_LEFT":
            if self.quantity > 1:
                self.quantity -= 1
                self._sound("qty_down")          # very short soft tick
            else:
                self._swipe_between_screens(event)   # already at 1
        elif event == "THUMBS_UP":
            self._add_selected_to_cart()
        return True

    def _on_discount(self, event):
        if event == "THUMBS_UP":
            self.go_to_screen(config.CONFIRM)
            self._sound("gesture")             # soft blip: on to Confirm
        elif event == "OPEN_PALM":
            self.screen = config.MENU      # add another coffee to the same order
            self._sound("gesture")
        return True

    def _on_confirm(self, event):
        if event == "THUMBS_UP":
            self.confirm_order()
        return True

    def _on_summary(self, event):
        if event == "THUMBS_UP":
            self.screen = config.COMPLETE
            self.complete_started_at = self._clock()
            self._sound("confirm")             # gentle ding on the Thank-you screen
            self.set_message("Enjoy your coffee!")
        return True

    def _on_complete(self, event):
        if event == "OPEN_PALM":
            self.start_new_order()
        return True

    # ============================================================ actions
    def select_product(self, product):
        """POINTING / clicking a card: choose this coffee."""
        if product is None:
            return False
        self.menu.select(product)
        self.quantity = 1
        self.screen = config.SELECT
        self._sound("select")
        self.set_message(f"{product.name} selected")
        return True

    def _add_selected_to_cart(self):
        """THUMBS_UP on the Quantity screen: put the coffee into the cart."""
        product = self.menu.selected_product
        if product is None:
            self.set_message("Choose a coffee first")
            return False
        try:
            self.cart.add_product(product, self.quantity)
        except ValueError as error:
            self.set_message(str(error))
            return False
        self.screen = config.DISCOUNT
        self._sound("add_cart")        # short cup clink: the coffee is in the cart
        self.set_message(f"{product.name} x {self.quantity} added")
        return True

    def confirm_order(self):
        """THUMBS_UP on Confirm: save the order and send it to the kitchen.

        Idempotent: when the confirm event arrives twice (double mouse click
        or a repeated gesture in the same frame), the already-saved order is
        reused instead of writing a duplicate order with the same cart.
        """
        if self.order_id is not None:
            return True                # already confirmed - never save twice
        if self.cart.is_empty():
            self._sound("empty")       # very subtle hint, never a harsh error
            self.set_message("Your order is empty")
            return False
        order_id = self.order_manager.create_order(self.cart)
        if order_id is None:
            self._sound("error")       # soft friendly "could not do that"
            self.set_message(self.order_manager.error_message or "Could not save the order")
            return False
        self.order_id = order_id
        self.kitchen.enqueue(order_id)
        self.screen = config.SUMMARY
        self._sound("success")         # short coffee-shop celebration
        # Small audio story, spaced out so the parts never overlap:
        # celebration -> ticket sent to the barista -> machine starts brewing.
        self._play_later("sent", 1.1)
        self._play_later("brew", 1.9)
        self.set_message(f"Order {format_order_number(order_id)} confirmed")
        return True

    def _apply_smile_discount(self):
        """SMILE: 10% discount, only on Discount / Confirm, once per order."""
        if self.screen not in (config.DISCOUNT, config.CONFIRM):
            return False
        if self.cart.apply_discount():
            self._sound("smile")       # cheerful - the fun moment of the app
            self.set_message(f"Nice smile! ☕ {config.DISCOUNT_PERCENT}% OFF!")
        elif self.cart.discount_applied:
            self.set_message("The discount was already applied")
        return True

    def go_back(self):
        """BLINK: return to the previous screen."""
        if self.screen not in self.BACK_SCREEN:
            self._sound("error")       # soft friendly hint - no warning beep
            self.set_message("You cannot go back from here")
            return
        if self.screen == config.DISCOUNT:      # undo the coffee we just added
            product = self.menu.selected_product
            if product is not None:
                self.cart.remove_product(product.name, self.quantity)
        self.screen = self.BACK_SCREEN[self.screen]
        self._sound("back")            # short reverse whoosh

    def cancel(self):
        """FIST: cancel the current choice or clear the whole order."""
        if self.screen in (config.SELECT, config.QUANTITY):
            self.menu.clear_selection()
            self.quantity = 1
            self.screen = config.MENU
            self._sound("cancel")
            self.set_message("Selection cancelled")
        elif self.screen in (config.MENU, config.DISCOUNT, config.CONFIRM):
            if self.cart.is_empty():
                self.set_message("Nothing to cancel")
                return
            self.cart.clear()
            self.screen = config.MENU
            self._sound("cancel")
            self.set_message("Order cleared")

    def clear_cart(self):
        """C key: clear the cart (not while a confirmed order is shown)."""
        if self.screen in (config.SUMMARY, config.COMPLETE):
            return
        if self.cart.is_empty():
            self.set_message("The cart is already empty")
            return
        self.cart.clear()
        self.menu.clear_selection()
        self.quantity = 1
        self._sound("cancel")
        self.set_message("Order cleared")

    def _swipe_between_screens(self, swipe):
        """SWIPE_RIGHT = next screen, SWIPE_LEFT = previous screen."""
        new_index = config.SCREEN_ORDER.index(self.screen) + (1 if swipe == "SWIPE_RIGHT" else -1)
        if 0 <= new_index < len(config.SCREEN_ORDER):
            self.go_to_screen(config.SCREEN_ORDER[new_index])
            self._sound("swipe")       # smooth whoosh between screens
        else:
            self._sound("error")       # soft end-of-stack hint
            self.set_message("This is the last screen" if new_index > 0 else "This is the first screen")

    def go_to_screen(self, screen_name):
        """Show any screen. Missing data is filled with a sample so a
        screen is never empty (used by the F1-F8 demo shortcuts)."""
        if screen_name == self.screen:
            return
        if screen_name == config.WELCOME or (
            self.order_id is not None and screen_name not in (config.SUMMARY, config.COMPLETE)
        ):
            # Welcome = new customer; a confirmed order cannot change
            self._reset_order()
        if screen_name not in (config.WELCOME, config.MENU) and self.menu.selected_product is None:
            sample = self.menu.products[2] if len(self.menu.products) > 2 else (
                self.menu.products[0] if self.menu.products else None)
            if sample is not None:
                self.menu.select(sample)          # sample: Latte (index 2)
        if screen_name in (config.DISCOUNT, config.CONFIRM, config.SUMMARY, config.COMPLETE) and self.cart.is_empty():
            product = self.menu.selected_product
            if product is not None:
                try:
                    self.cart.add_product(product, self.quantity)
                except ValueError:
                    pass
        if screen_name in (config.SUMMARY, config.COMPLETE) and self.order_id is None:
            order_id = self.order_manager.create_order(self.cart)   # demo jump: make it real
            if order_id is not None:
                self.order_id = order_id
                self.kitchen.enqueue(order_id)
        if screen_name == config.COMPLETE:
            self.complete_started_at = self._clock()
        self.screen = screen_name

    def start_new_order(self):
        """Clear everything and return to the Welcome screen."""
        self._reset_order()
        self.message = ""
        self.screen = config.WELCOME
        self._sound("welcome")         # a new customer walks into the shop

    def _reset_order(self):
        self.cart.clear()
        self.menu.clear_selection()
        self.menu.go_to_page(0)
        self.quantity = 1
        self.order_id = None

    # ============================================================ mouse bridge
    def perform(self, action, value=None):
        """Run a button action coming from the mouse (or another direct command).

        The renderer names every button ('start', 'card', 'next_page', ...)
        and main.py passes the name here.
        """
        if action == "start":
            self.handle_event("OPEN_PALM")
        elif action == "card":
            self.select_product(value)
        elif action == "step":
            self.go_to_screen(value)
            self._sound("gesture")
        elif action == "prev_page":
            if not self.menu.previous_page():
                self.set_message("You are on the first page")
            else:
                self._sound("swipe")        # whoosh: previous coffee page
        elif action == "next_page":
            if not self.menu.next_page():
                self.set_message("You are on the last page")
            else:
                self._sound("swipe")        # whoosh: next coffee page
        elif action == "qty_minus":
            if self.quantity > 1:
                self.quantity -= 1
                self._sound("qty_down")     # very short soft tick
            else:
                self.set_message("Minimum quantity is 1")
        elif action == "qty_plus":
            if self.quantity < config.MAX_QUANTITY:
                self.quantity += 1
                self._sound("qty_up")       # very short soft tick
            else:
                self.set_message(f"Maximum quantity is {config.MAX_QUANTITY}")
        elif action == "continue":
            self.handle_event("THUMBS_UP")
        elif action == "confirm":
            self.confirm_order()
        elif action == "back":
            self.go_back()
        elif action == "clear":
            self.clear_cart()
        elif action == "add_another":
            self.screen = config.MENU
            self._sound("gesture")
        elif action == "new_order":
            self.start_new_order()

    def update(self):
        """Call once per frame: expire toasts and auto-close the Done screen."""
        now = self._clock()
        if self.message and now >= self.message_until:
            self.message = ""
        if self.screen == config.COMPLETE and now - self.complete_started_at >= config.COMPLETE_SECONDS:
            self.start_new_order()
