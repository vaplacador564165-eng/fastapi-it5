"""SQLite database connection and table setup for the supply inventory system."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DATABASE_FILE = Path(__file__).resolve().parent.parent / "inventory.db"


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    # SQLite does not enforce foreign keys unless this is enabled per connection.
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                price REAL NOT NULL CHECK (price >= 0),
                category_id INTEGER REFERENCES categories (id) ON DELETE RESTRICT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES items (id) ON DELETE RESTRICT,
                movement_type TEXT NOT NULL CHECK (movement_type IN ('ISSUE', 'RESTOCK')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                issued_to TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
