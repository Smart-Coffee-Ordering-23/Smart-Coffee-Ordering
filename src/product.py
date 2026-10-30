"""Product model - one coffee on the menu.
This file only holds data. It has no drawing code and no database code,
so it can be reused by the menu, the cart and the tests.
"""
from dataclasses import dataclass
CURRENCY_SYMBOL = "$"
@dataclass
class Product:
    """A single coffee that can be ordered."""
    id: int
    name: str
    price: float
    image: str = ""           
    description: str = ""     

    @classmethod
    def from_dict(cls, data):
        """Build a Product from one dictionary of data/menu.json.
        Raises ValueError with a friendly message when required fields
        are missing or wrong, so a broken menu.json is easy to find.
        """
        if not isinstance(data, dict):
            raise ValueError("each product must be a JSON object")
        if "name" not in data or not str(data["name"]).strip():
            raise ValueError("product is missing a name")
        if "price" not in data:
            raise ValueError(f"product '{data['name']}' is missing a price")
        try:
            price = float(data["price"])
        except (TypeError, ValueError):
            raise ValueError(f"product '{data['name']}' has a non-numeric price")
        if price < 0:
            raise ValueError(f"product '{data['name']}' has a negative price")
        try:
            product_id = int(data.get("id", 0))
        except (TypeError, ValueError):
            raise ValueError(f"product '{data['name']}' has a non-numeric id")

        return cls(
            id=product_id,
            name=str(data["name"]).strip(),
            price=round(price, 2),
            image=str(data.get("image", "")),
            description=str(data.get("description", "")),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "image": self.image,
            "description": self.description,
        }
def format_price(amount):
    """Turn 2.5 into '$2.50'."""
    return f"{CURRENCY_SYMBOL}{float(amount):.2f}"