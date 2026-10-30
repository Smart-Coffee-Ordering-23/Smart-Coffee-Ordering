"""KitchenQueue - a very simple kitchen order queue.
    Order confirmed -> Kitchen Queue -> Preparing -> Completed
The queue also updates the order status inside the database through the
OrderManager, so the UI can show:  Order #001  Status: Preparing
"""
import time
from src import config
from src.order_manager import STATUS_COMPLETED, STATUS_PREPARING
class KitchenQueue:
    """Keeps track of confirmed orders that the kitchen is working on."""
    def __init__(self, order_manager=None, prepare_seconds=None, clock=None):
        self.order_manager = order_manager
        self.prepare_seconds = (config.KITCHEN_PREPARE_SECONDS
                                if prepare_seconds is None else prepare_seconds)
        self._clock = clock or time.time
        self._entries = {}          
        self._completed_events = [] 

    def enqueue(self, order_id):
        """A new confirmed order starts Preparing."""
        if order_id is None:
            return None
        entry = {"status": STATUS_PREPARING, "started_at": self._clock()}
        self._entries[order_id] = entry
        if self.order_manager is not None:
            self.order_manager.update_status(order_id, STATUS_PREPARING)
        return entry

    def update(self):
        """Call once per frame: finishes orders after the preparation time."""
        now = self._clock()
        for order_id, entry in self._entries.items():
            if entry["status"] == STATUS_PREPARING and now - entry["started_at"] >= self.prepare_seconds:
                entry["status"] = STATUS_COMPLETED
                if self.order_manager is not None:
                    self.order_manager.update_status(order_id, STATUS_COMPLETED)
                self._completed_events.append(order_id)

    def pop_completed_events(self):
        """Order ids that became Completed since the last call (for sounds/toasts)."""
        events = self._completed_events
        self._completed_events = []
        return events

    def get_status(self, order_id):
        """'Preparing' / 'Completed', or None for unknown orders."""
        entry = self._entries.get(order_id)
        return entry["status"] if entry else None

    def recent(self, limit=3):
        """The last few orders with their status, newest first."""
        items = list(self._entries.items())[-limit:]
        return [(order_id, entry["status"]) for order_id, entry in reversed(items)]

    def clear(self):
        self._entries.clear()
        self._completed_events.clear()