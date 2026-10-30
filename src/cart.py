"""Cart - quantities, subtotal, discount and total.

The cart only calculates and stores. It contains NO drawing code and
NO database code, so it is easy to test.
"""
from dataclasses import dataclass

from src import config
from src.product import Product

MAX_QUANTITY = config.MAX_QUANTITY
DISCOUNT_PERCENT = config.DISCOUNT_PERCENT
@dataclass
class CartItem:
    """One line of the cart, for example: Latte x 2."""
    product_id: int
    name: str
    unit_price: float
    quantity: int = 1

    def line_total(self):
        return round(self.unit_price * self.quantity, 2)
class Cart:
    """The customer's shopping cart."""

    def __init__(self):
        self.items = []
        self.discount_applied = False

    def add_product(self, product, quantity=1):
        """Add a Product (or increase an existing line). Raises ValueError for bad input."""
        self._check_quantity(quantity)
        if not isinstance(product, Product):
            raise ValueError("add_product expects a Product.")

        existing = self._find_item(product.id)
        if existing is None:
            self.items.append(CartItem(product.id, product.name, product.price, quantity))
        else:
            self._check_quantity(existing.quantity + quantity)
            existing.quantity += quantity

    def remove_product(self, name, quantity=None):
        """Remove some cups of a coffee. quantity=None removes the whole line."""
        item = self._find_item_by_name(name)
        if item is None:
            return
        if quantity is None or quantity >= item.quantity:
            self.items.remove(item)
        else:
            item.quantity -= quantity

    def increase_quantity(self, name):
        """One more cup of this coffee. Returns False when the maximum is reached."""
        item = self._find_item_by_name(name)
        if item is None:
            return False
        if item.quantity >= MAX_QUANTITY:
            return False
        item.quantity += 1
        return True

    def decrease_quantity(self, name):
        """One cup less. The line disappears with its last cup."""
        item = self._find_item_by_name(name)
        if item is None:
            return False
        if item.quantity <= 1:
            self.items.remove(item)
        else:
            item.quantity -= 1
        return True

    def clear(self):
        """Empty the cart and forget the discount."""
        self.items = []
        self.discount_applied = False

    def subtotal(self):
        return round(sum(item.line_total() for item in self.items), 2)

    def discount_amount(self):
        if not self.discount_applied:
            return 0.0
        return round(self.subtotal() * DISCOUNT_PERCENT / 100, 2)

    def total(self):
        return round(self.subtotal() - self.discount_amount(), 2)

    def total_quantity(self):
        return sum(item.quantity for item in self.items)

    def is_empty(self):
        return len(self.items) == 0

    def apply_discount(self):
        """Apply the smile discount (10%). Only once per order.
        Returns False when it cannot be applied."""
        if self.is_empty() or self.discount_applied:
            return False
        self.discount_applied = True
        return True

    def get_item(self, name):
        return self._find_item_by_name(name)

    def _find_item(self, product_id):
        for item in self.items:
            if item.product_id == product_id:
                return item
        return None

    def _find_item_by_name(self, name):
        for item in self.items:
            if item.name == name:
                return item
        return None

    @staticmethod
    def _check_quantity(quantity):
        is_whole_number = isinstance(quantity, int) and not isinstance(quantity, bool)
        if not is_whole_number or not 1 <= quantity <= MAX_QUANTITY:
            raise ValueError(f"Quantity must be a whole number from 1 to {MAX_QUANTITY}.")