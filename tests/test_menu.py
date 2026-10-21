"""Menu tests - loading data/menu.json, paging and selection.

Recreated after the original file was lost (see .pytest_cache node ids).
"""
import json

from src import config
from src.menu_manager import MenuManager


def test_menu_json_loads():
    menu = MenuManager()
    assert menu.error_message == ""
    assert len(menu.products) == 12


def test_product_ids_are_unique():
    menu = MenuManager()
    ids = [product.id for product in menu.products]
    assert len(set(ids)) == len(ids)


def test_product_data_is_valid():
    menu = MenuManager()
    for product in menu.products:
        assert product.id > 0
        assert product.name
        assert product.price > 0
        assert product.description


def test_product_images_exist():
    menu = MenuManager()
    for product in menu.products:
        assert menu.get_image_path(product) is not None, product.name
        assert menu.get_image_path(product).exists(), product.name


def test_two_pages_of_six():
    menu = MenuManager()
    assert menu.page_count == 2
    assert len(menu.current_products) == 6


def test_both_pages_cover_all_twelve():
    menu = MenuManager()
    seen = [p.id for p in menu.current_products]
    menu.next_page()
    seen += [p.id for p in menu.current_products]
    assert sorted(seen) == sorted(p.id for p in menu.products)


def test_page_navigation():
    menu = MenuManager()
    assert menu.can_go_previous is False
    assert menu.can_go_next is True
    assert menu.next_page() is True
    assert menu.can_go_next is False
    assert menu.previous_page() is True


def test_product_selection():
    menu = MenuManager()
    product = menu.products[4]
    assert menu.select(product) is product
    assert menu.selected_product is product
    # the page jumps to the one that contains the selection
    assert product in menu.current_products


def test_unknown_product_is_not_selected():
    menu = MenuManager()
    assert menu.select(9999) is None
    assert menu.selected_product is None


def test_missing_file_is_handled(tmp_path):
    menu = MenuManager(menu_file=tmp_path / "nope.json")
    assert menu.products == []
    assert "not found" in menu.error_message.lower()


def test_invalid_json_is_handled(tmp_path):
    broken = tmp_path / "menu.json"
    broken.write_text("{ not json", encoding="utf-8")
    menu = MenuManager(menu_file=broken)
    assert menu.products == []
    assert "JSON" in menu.error_message


def test_real_menu_file_is_valid_json():
    data = json.loads(config.MENU_FILE.read_text(encoding="utf-8"))
    assert isinstance(data["products"], list)
