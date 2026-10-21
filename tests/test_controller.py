"""Focused tests for InteractionController behaviour that protects data.

Found while debugging: confirm_order() could be triggered twice in one frame
(double mouse click / repeated event) and created TWO orders with the same
cart, because it never checked whether the order was already confirmed.
"""
from src import config
from src.cart import Cart
from src.interaction_controller import InteractionController
from src.kitchen_queue import KitchenQueue
from src.menu_manager import MenuManager


class CountingOrders:
    """OrderManager stand-in that records every create_order call."""

    error_message = ""

    def __init__(self):
        self.calls = 0
        self._next_id = 1

    def create_order(self, cart):
        self.calls += 1
        order_id = self._next_id
        self._next_id += 1
        return order_id


def make_controller():
    orders = CountingOrders()
    controller = InteractionController(MenuManager(), Cart(), orders,
                                       KitchenQueue(), audio=None)
    return controller, orders


def make_full_cart(controller):
    product = controller.menu.products[0]
    controller.select_product(product)          # -> SELECT
    controller.screen = config.QUANTITY
    controller.quantity = 2
    controller._add_selected_to_cart()          # -> DISCOUNT
    controller.screen = config.CONFIRM


def test_double_confirm_creates_only_one_order():
    """A double click / double event on Confirm must NOT duplicate the order."""
    controller, orders = make_controller()
    make_full_cart(controller)

    assert controller.confirm_order() is True     # first click: order saved
    assert controller.confirm_order() is True     # second click: still fine

    assert orders.calls == 1                      # the bug: this was 2
    assert controller.order_id == 1


def test_confirm_after_go_to_screen_summary_does_not_reorder():
    """Jumping to the summary again must not save the same cart twice."""
    controller, orders = make_controller()
    make_full_cart(controller)
    controller.confirm_order()
    controller.go_to_screen(config.SUMMARY)       # second jump with order_id set
    assert orders.calls == 1


def test_new_order_resets_before_next_confirmation():
    """After starting a new order the customer can confirm again."""
    controller, orders = make_controller()
    make_full_cart(controller)
    controller.confirm_order()
    controller.start_new_order()                  # back to WELCOME
    make_full_cart(controller)
    assert controller.confirm_order() is True
    assert orders.calls == 2                      # a genuinely new order
