"""OrderManager - saves and reads orders in SQLite (data/orders.db).

Tables:
    orders      - order ID, date/time, subtotal, discount, total, status
    order_items - order ID, product ID, product name, quantity, price

All SQL uses parameterized queries (no string building with user input).
If the database cannot be used the app keeps running and error_message
explains the problem.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from src import config

# Order statuses used across the project
STATUS_CONFIRMED = "Confirmed"
STATUS_PREPARING = "Preparing"
STATUS_COMPLETED = "Completed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    subtotal   REAL    NOT NULL,
    discount   REAL    NOT NULL,
    total      REAL    NOT NULL,
    status     TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    product_name TEXT    NOT NULL,
    quantity     INTEGER NOT NULL,
    price        REAL    NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (id)
);
"""


def format_order_number(order_id):
    """Turn the database id 1 into '#001'."""
    return f"#{int(order_id):03d}"


class OrderManager:
    """Creates, saves and updates orders in the local SQLite database."""

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else config.DATABASE_FILE
        self.connection = None
        self.error_message = ""
        self._connect()

    # ------------------------------------------------------------- connection
    def _connect(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.executescript(_SCHEMA)
            self.connection.commit()
        except (sqlite3.Error, OSError) as error:
            self.error_message = f"Database error: {error}"
            self.connection = None
            print(f"[OrderManager] {self.error_message}")

    @property
    def is_available(self):
        return self.connection is not None

    # ------------------------------------------------------------- creating
    def create_order(self, cart):
        """Save a confirmed cart as a new order.

        Returns the new order id (int), or None when the database failed.
        """
        if self.connection is None or cart.is_empty():
            return None
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO orders (created_at, subtotal, discount, total, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    cart.subtotal(),
                    cart.discount_amount(),
                    cart.total(),
                    STATUS_CONFIRMED,
                ),
            )
            order_id = cursor.lastrowid
            for item in cart.items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (order_id, item.product_id, item.name, item.quantity, item.unit_price),
                )
            self.connection.commit()
            self.error_message = ""
            return order_id
        except sqlite3.Error as error:
            self.connection.rollback()
            self.error_message = f"Could not save the order: {error}"
            print(f"[OrderManager] {self.error_message}")
            return None

    # ------------------------------------------------------------- reading
    def get_order(self, order_id):
        """Return one order as a dict with its items, or None."""
        if self.connection is None:
            return None
        try:
            row = self.connection.execute(
                "SELECT id, created_at, subtotal, discount, total, status "
                "FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            if row is None:
                return None
            order = dict(row)
            order["items"] = [dict(item) for item in self.connection.execute(
                "SELECT product_id, product_name, quantity, price "
                "FROM order_items WHERE order_id = ? ORDER BY id",
                (order_id,),
            ).fetchall()]
            return order
        except sqlite3.Error as error:
            self.error_message = f"Could not read the order: {error}"
            print(f"[OrderManager] {self.error_message}")
            return None

    def get_orders(self, limit=20):
        """Return the most recent orders (newest first)."""
        if self.connection is None:
            return []
        try:
            rows = self.connection.execute(
                "SELECT id, created_at, subtotal, discount, total, status "
                "FROM orders ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            self.error_message = f"Could not read orders: {error}"
            print(f"[OrderManager] {self.error_message}")
            return []

    def count_orders(self):
        if self.connection is None:
            return 0
        try:
            row = self.connection.execute("SELECT COUNT(*) AS n FROM orders").fetchone()
            return int(row["n"])
        except sqlite3.Error:
            return 0

    # ------------------------------------------------------------- status
    def update_status(self, order_id, status):
        """Update the status of an order. Returns True on success."""
        if self.connection is None:
            return False
        try:
            cursor = self.connection.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id),
            )
            self.connection.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as error:
            self.error_message = f"Could not update the status: {error}"
            print(f"[OrderManager] {self.error_message}")
            return False

    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except sqlite3.Error:
                pass
            self.connection = None
