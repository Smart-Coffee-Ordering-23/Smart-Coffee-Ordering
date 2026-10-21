"""One-off helper to inspect data/orders.db (development only)."""
import sqlite3

conn = sqlite3.connect("data/orders.db")
conn.row_factory = sqlite3.Row
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("TABLES:", tables)
for t in tables:
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})")]
    n = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
    print(f"  {t}: {n} rows | cols={cols}")
print("--- last 10 orders ---")
for r in conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10"):
    print(dict(r))
print("--- order_items sample ---")
for r in conn.execute("SELECT * FROM order_items ORDER BY id DESC LIMIT 10"):
    print(dict(r))
print("--- schema ---")
for r in conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
    print(r[0])
conn.close()
