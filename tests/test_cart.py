"""Cart tests - quantities, subtotal, discount and total.

Recreated after the original file was lost (see .pytest_cache node ids).
Covers the same behaviour that src/cart.py implements today.
"""
import pytest

from src.cart import Cart, MAX_QUANTITY
from src.product import Product


def latte():
    return Product(id=3, name="Latte", price=2.50)


def mocha():
    return Product(id=5, name="Mocha", price=2.90)


def test_new_cart_is_empty():
    cart = Cart()
    assert cart.is_empty()
    assert cart.items == []
    assert cart.total_quantity() == 0


def test_add_product():
    cart = Cart()
    cart.add_product(latte())
    assert len(cart.items) == 1
    assert cart.get_item("Latte").quantity == 1


def test_same_product_is_merged():
    cart = Cart()
    cart.add_product(latte(), 2)
    cart.add_product(latte(), 3)
    assert len(cart.items) == 1
    assert cart.get_item("Latte").quantity == 5


def test_remove_product():
    cart = Cart()
    cart.add_product(latte(), 2)
    cart.remove_product("Latte", 1)
    assert cart.get_item("Latte").quantity == 1
    cart.remove_product("Latte")
    assert cart.is_empty()


def test_increase_quantity():
    cart = Cart()
    cart.add_product(latte())
    assert cart.increase_quantity("Latte") is True
    assert cart.get_item("Latte").quantity == 2


def test_increase_stops_at_maximum():
    cart = Cart()
    cart.add_product(latte(), MAX_QUANTITY)
    assert cart.increase_quantity("Latte") is False
    assert cart.get_item("Latte").quantity == MAX_QUANTITY


def test_decrease_quantity():
    cart = Cart()
    cart.add_product(latte(), 2)
    assert cart.decrease_quantity("Latte") is True
    assert cart.get_item("Latte").quantity == 1


def test_decrease_removes_last_cup():
    cart = Cart()
    cart.add_product(latte())
    cart.decrease_quantity("Latte")
    assert cart.is_empty()


def test_invalid_quantity_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_product(latte(), 0)
    with pytest.raises(ValueError):
        cart.add_product(latte(), MAX_QUANTITY + 1)
    with pytest.raises(ValueError):
        cart.add_product(latte(), 1.5)


def test_multiple_products_subtotal():
    cart = Cart()
    cart.add_product(latte(), 2)      # 5.00
    cart.add_product(mocha())         # 2.90
    assert cart.subtotal() == 7.90


def test_total_without_discount_equals_subtotal():
    cart = Cart()
    cart.add_product(latte(), 3)
    assert cart.total() == cart.subtotal() == 7.50


def test_discount_is_10_percent():
    cart = Cart()
    cart.add_product(latte(), 2)
    assert cart.apply_discount() is True
    assert cart.discount_amount() == 0.50
    assert cart.total() == 4.50


def test_discount_only_once():
    cart = Cart()
    cart.add_product(latte())
    cart.apply_discount()
    assert cart.apply_discount() is False
    assert cart.discount_amount() == 0.25


def test_discount_on_empty_cart_is_refused():
    cart = Cart()
    assert cart.apply_discount() is False
    assert cart.discount_applied is False


def test_clear_cart():
    cart = Cart()
    cart.add_product(latte(), 2)
    cart.apply_discount()
    cart.clear()
    assert cart.is_empty()
    assert cart.discount_applied is False


def test_total_quantity():
    cart = Cart()
    cart.add_product(latte(), 2)
    cart.add_product(mocha(), 3)
    assert cart.total_quantity() == 5
