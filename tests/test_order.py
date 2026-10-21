"""Order + kitchen-queue tests on a throwaway database.

Recreated after the original file was lost (see .pytest_cache node ids).
Every test uses its own temp database - the real data/orders.db is never
touched (an integration check for the real file is at the very bottom).
"""
from src.cart import Cart
from src.kitchen_queue import KitchenQueue
from src.order_manager import (OrderManager, STATUS_COMPLETED,
                               STATUS_CONFIRMED, STATUS_PREPARING,
                               format_order_number)
from src.product import Product


def make_cart():
    cart = Cart()
    cart.add_product(Product(id=3, name="Latte", price=2.50), 2)
    return cart


def test_database_file_created(tmp_path):
    db = tmp_path / "orders.db"
    manager = OrderManager(db_path=db)
    assert db.exists()
    assert manager.is_available
    manager.close()


def test_create_order_saves_to_sqlite(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    order_id = manager.create_order(make_cart())
    assert isinstance(order_id, int)
    order = manager.get_order(order_id)
    assert order is not None
    assert order["status"] == STATUS_CONFIRMED
    manager.close()


def test_order_values_are_saved(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    order_id = manager.create_order(make_cart())
    order = manager.get_order(order_id)
    assert order["subtotal"] == 5.00
    assert order["discount"] == 0.0
    assert order["total"] == 5.00
    manager.close()


def test_order_items_are_saved(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    order_id = manager.create_order(make_cart())
    items = manager.get_order(order_id)["items"]
    assert len(items) == 1
    assert items[0]["product_name"] == "Latte"
    assert items[0]["quantity"] == 2
    assert items[0]["price"] == 2.50
    manager.close()


def test_empty_cart_is_not_saved(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    assert manager.create_order(Cart()) is None
    assert manager.count_orders() == 0
    manager.close()


def test_get_orders_newest_first(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    first = manager.create_order(make_cart())
    second = manager.create_order(make_cart())
    orders = manager.get_orders()
    assert [o["id"] for o in orders] == [second, first]
    manager.close()


def test_update_status(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    order_id = manager.create_order(make_cart())
    assert manager.update_status(order_id, STATUS_PREPARING) is True
    assert manager.get_order(order_id)["status"] == STATUS_PREPARING
    assert manager.update_status(9999, STATUS_COMPLETED) is False
    manager.close()


def test_order_number_format():
    assert format_order_number(1) == "#001"
    assert format_order_number(42) == "#042"
    assert format_order_number(1234) == "#1234"


# ================================================================ kitchen
def test_kitchen_queue_flow(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    clock = {"now": 1000.0}
    queue = KitchenQueue(order_manager=manager, prepare_seconds=8,
                         clock=lambda: clock["now"])
    order_id = manager.create_order(make_cart())
    queue.enqueue(order_id)
    assert queue.get_status(order_id) == STATUS_PREPARING
    assert manager.get_order(order_id)["status"] == STATUS_PREPARING

    clock["now"] += 9           # preparation finished
    queue.update()
    assert queue.get_status(order_id) == STATUS_COMPLETED
    assert manager.get_order(order_id)["status"] == STATUS_COMPLETED
    manager.close()


def test_kitchen_queue_events_are_consumed(tmp_path):
    manager = OrderManager(db_path=tmp_path / "orders.db")
    clock = {"now": 0.0}
    queue = KitchenQueue(order_manager=manager, prepare_seconds=1,
                         clock=lambda: clock["now"])
    order_id = manager.create_order(make_cart())
    queue.enqueue(order_id)
    clock["now"] += 2
    queue.update()
    assert queue.pop_completed_events() == [order_id]
    assert queue.pop_completed_events() == []      # consumed once
    manager.close()


# ==================================================== real database safety
def test_real_database_still_has_the_historical_orders():
    """The 5 pre-existing kiosk orders must never be lost or altered."""
    manager = OrderManager()                      # data/orders.db
    assert manager.is_available
    assert manager.count_orders() >= 5
    manager.close()
