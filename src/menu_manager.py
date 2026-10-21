"""MenuManager - loads data/menu.json and handles paging and selection.

The JSON file is the only place where coffee data lives.
This class never draws anything; the renderer asks it for the current page.
"""
import json
from pathlib import Path

from src import config
from src.product import Product


class MenuManager:
    """Loads the coffee menu and remembers the current page and selection."""

    def __init__(self, menu_file=None):
        self.menu_file = Path(menu_file) if menu_file else config.MENU_FILE
        self.products = []
        self.page = 0
        self.selected_id = None
        self.error_message = ""
        self.load()

    # ------------------------------------------------------------- loading
    def load(self):
        """Read menu.json. On any problem the menu stays empty and
        error_message explains what happened (the app keeps running)."""
        self.products = []
        self.page = 0
        self.selected_id = None
        self.error_message = ""

        try:
            raw_text = self.menu_file.read_text(encoding="utf-8")
        except OSError as error:
            self.error_message = f"Menu file not found: {self.menu_file.name}"
            print(f"[MenuManager] {error}")
            return

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as error:
            self.error_message = "menu.json is not valid JSON - check its syntax"
            print(f"[MenuManager] {error}")
            return

        # Accept either {"products": [...]} or a plain list [...]
        if isinstance(data, dict):
            entries = data.get("products", [])
        else:
            entries = data
        if not isinstance(entries, list):
            self.error_message = "menu.json must contain a list of products"
            return

        for index, entry in enumerate(entries, start=1):
            try:
                product = Product.from_dict(entry)
            except ValueError as error:
                self.error_message = f"Invalid product #{index}: {error}"
                print(f"[MenuManager] {self.error_message}")
                continue
            if product.id <= 0:          # give an id to entries that forgot one
                product.id = index
            self.products.append(product)

        if not self.products and not self.error_message:
            self.error_message = "menu.json contains no products"

    # ------------------------------------------------------------- paging
    @property
    def page_count(self):
        return max(1, (len(self.products) + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE)

    @property
    def current_products(self):
        """The products that belong on the current page (up to 6)."""
        start = self.page * config.ITEMS_PER_PAGE
        return self.products[start:start + config.ITEMS_PER_PAGE]

    @property
    def can_go_next(self):
        return self.page < self.page_count - 1

    @property
    def can_go_previous(self):
        return self.page > 0

    def next_page(self):
        if self.can_go_next:
            self.page += 1
            return True
        return False

    def previous_page(self):
        if self.can_go_previous:
            self.page -= 1
            return True
        return False

    def go_to_page(self, page):
        if 0 <= page < self.page_count:
            self.page = page
            return True
        return False

    # ------------------------------------------------------------- selection
    @property
    def selected_product(self):
        return self.get_product(self.selected_id)

    def select(self, product_or_id):
        """Remember the chosen coffee. Accepts a Product, an id, or None."""
        if product_or_id is None:
            self.selected_id = None
            return None
        product = product_or_id
        if isinstance(product_or_id, int):
            product = self.get_product(product_or_id)
        if product is None:
            return None
        self.selected_id = product.id
        # Make sure the page containing the product is visible
        for index, candidate in enumerate(self.products):
            if candidate.id == product.id:
                self.go_to_page(index // config.ITEMS_PER_PAGE)
                break
        return product

    def clear_selection(self):
        self.selected_id = None

    def get_product(self, product_id):
        if product_id is None:
            return None
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    # ------------------------------------------------------------- images
    def get_image_path(self, product):
        """Return this product's image path.

        Only the product's own file is ever used - a missing image is
        never replaced by a different coffee (the renderer shows a
        placeholder instead).
        """
        image_name = getattr(product, "image", "") or ""
        if not image_name:
            return None
        candidate = config.PROJECT_ROOT / image_name
        if candidate.exists():
            return candidate
        # Search the known image folders by file name
        file_name = Path(image_name).name
        for folder in config.PRODUCT_IMAGE_DIRS:
            image_path = folder / file_name
            if image_path.exists():
                return image_path
        return candidate          # missing -> renderer draws a placeholder
