"""Inventory schemas, domain errors, and database operations."""

import sqlite3
from typing import Any, Callable

from pydantic import BaseModel, Field

ITEM_SELECT = """
    SELECT items.id, items.name, items.description, items.quantity, items.price,
           items.category_id, categories.name AS category_name
    FROM items
    LEFT JOIN categories ON categories.id = items.category_id
"""

MOVEMENT_SELECT = (
    "SELECT id, item_id, movement_type, quantity, issued_to, note, created_at "
    "FROM stock_movements"
)


class InventoryError(Exception):
    """Base class for errors the API turns into HTTP responses."""


class ItemNotFoundError(InventoryError):
    pass


class CategoryNotFoundError(InventoryError):
    pass


class DuplicateCategoryError(InventoryError):
    pass


class RecordInUseError(InventoryError):
    """Raised when a delete is blocked by a foreign key reference."""


class InsufficientStockError(InventoryError):
    def __init__(self, available: int, requested: int) -> None:
        super().__init__(f"Only {available} in stock, {requested} requested")
        self.available = available
        self.requested = requested


def _fetch_item(connection: sqlite3.Connection, item_id: int) -> dict[str, Any] | None:
    row = connection.execute(ITEM_SELECT + " WHERE items.id = ?", (item_id,)).fetchone()
    return dict(row) if row is not None else None


def _require_category(connection: sqlite3.Connection, category_id: int | None) -> None:
    if category_id is None:
        return
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if row is None:
        raise CategoryNotFoundError("Category not found")


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class Category(CategoryInput):
    id: int

    @staticmethod
    def list_categories(database_connection: Callable) -> list[dict[str, Any]]:
        with database_connection() as connection:
            rows = connection.execute(
                "SELECT id, name FROM categories ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_category(category_id: int, database_connection: Callable) -> dict[str, Any] | None:
        with database_connection() as connection:
            row = connection.execute(
                "SELECT id, name FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    @staticmethod
    def create_category(
        category_input: CategoryInput, database_connection: Callable
    ) -> dict[str, Any]:
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)",
                    (category_input.name.strip(),),
                )
                category_id = cursor.lastrowid
        except sqlite3.IntegrityError as error:
            raise DuplicateCategoryError("Category name already exists") from error
        return {"id": category_id, "name": category_input.name.strip()}

    @staticmethod
    def update_category(
        category_id: int, category_input: CategoryInput, database_connection: Callable
    ) -> dict[str, Any] | None:
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "UPDATE categories SET name = ? WHERE id = ?",
                    (category_input.name.strip(), category_id),
                )
                if cursor.rowcount == 0:
                    return None
        except sqlite3.IntegrityError as error:
            raise DuplicateCategoryError("Category name already exists") from error
        return {"id": category_id, "name": category_input.name.strip()}

    @staticmethod
    def delete_category(category_id: int, database_connection: Callable) -> bool:
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "DELETE FROM categories WHERE id = ?", (category_id,)
                )
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as error:
            raise RecordInUseError("Category still has items assigned to it") from error


class ItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    quantity: int = Field(ge=0)
    price: float = Field(ge=0)
    category_id: int | None = None


class Item(ItemInput):
    id: int

    @staticmethod
    def list_items(
        database_connection: Callable,
        search: str | None = None,
        category_id: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if search:
            conditions.append("(items.name LIKE ? OR items.description LIKE ?)")
            pattern = f"%{search}%"
            parameters.extend([pattern, pattern])
        if category_id is not None:
            conditions.append("items.category_id = ?")
            parameters.append(category_id)
        query = ITEM_SELECT
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY items.id"
        with database_connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def list_low_stock(threshold: int, database_connection: Callable) -> list[dict[str, Any]]:
        with database_connection() as connection:
            rows = connection.execute(
                ITEM_SELECT + " WHERE items.quantity <= ? ORDER BY items.quantity, items.id",
                (threshold,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_item(item_id: int, database_connection: Callable) -> dict[str, Any] | None:
        with database_connection() as connection:
            return _fetch_item(connection, item_id)

    @staticmethod
    def create_item(item_input: ItemInput, database_connection: Callable) -> dict[str, Any]:
        with database_connection() as connection:
            _require_category(connection, item_input.category_id)
            cursor = connection.execute(
                "INSERT INTO items (name, description, quantity, price, category_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    item_input.name.strip(),
                    item_input.description,
                    item_input.quantity,
                    item_input.price,
                    item_input.category_id,
                ),
            )
            return _fetch_item(connection, cursor.lastrowid)

    @staticmethod
    def update_item(
        item_id: int, item_input: ItemInput, database_connection: Callable
    ) -> dict[str, Any] | None:
        with database_connection() as connection:
            _require_category(connection, item_input.category_id)
            cursor = connection.execute(
                "UPDATE items SET name = ?, description = ?, quantity = ?, price = ?, "
                "category_id = ? WHERE id = ?",
                (
                    item_input.name.strip(),
                    item_input.description,
                    item_input.quantity,
                    item_input.price,
                    item_input.category_id,
                    item_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
            return _fetch_item(connection, item_id)

    @staticmethod
    def delete_item(item_id: int, database_connection: Callable) -> bool:
        try:
            with database_connection() as connection:
                cursor = connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as error:
            raise RecordInUseError(
                "Item has stock movement history and cannot be deleted"
            ) from error


class IssueInput(BaseModel):
    quantity: int = Field(gt=0)
    issued_to: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)


class RestockInput(BaseModel):
    quantity: int = Field(gt=0)
    note: str = Field(default="", max_length=500)


class StockMovement(BaseModel):
    id: int
    item_id: int
    movement_type: str
    quantity: int
    issued_to: str
    note: str
    created_at: str

    @staticmethod
    def list_for_item(item_id: int, database_connection: Callable) -> list[dict[str, Any]]:
        with database_connection() as connection:
            if _fetch_item(connection, item_id) is None:
                raise ItemNotFoundError("Item not found")
            rows = connection.execute(
                MOVEMENT_SELECT + " WHERE item_id = ? ORDER BY id DESC", (item_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _record(
        connection: sqlite3.Connection,
        item_id: int,
        movement_type: str,
        quantity: int,
        issued_to: str,
        note: str,
    ) -> dict[str, Any]:
        cursor = connection.execute(
            "INSERT INTO stock_movements (item_id, movement_type, quantity, issued_to, note) "
            "VALUES (?, ?, ?, ?, ?)",
            (item_id, movement_type, quantity, issued_to, note),
        )
        row = connection.execute(
            MOVEMENT_SELECT + " WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    @staticmethod
    def issue_stock(
        item_id: int, issue_input: IssueInput, database_connection: Callable
    ) -> dict[str, Any]:
        """Issue supplies: lower the item quantity and log the movement in one transaction."""
        with database_connection() as connection:
            item = _fetch_item(connection, item_id)
            if item is None:
                raise ItemNotFoundError("Item not found")
            # The WHERE clause makes the stock check and the decrement a single atomic step.
            cursor = connection.execute(
                "UPDATE items SET quantity = quantity - ? WHERE id = ? AND quantity >= ?",
                (issue_input.quantity, item_id, issue_input.quantity),
            )
            if cursor.rowcount == 0:
                raise InsufficientStockError(item["quantity"], issue_input.quantity)
            movement = StockMovement._record(
                connection,
                item_id,
                "ISSUE",
                issue_input.quantity,
                issue_input.issued_to.strip(),
                issue_input.note,
            )
            return {"movement": movement, "item": _fetch_item(connection, item_id)}

    @staticmethod
    def restock_item(
        item_id: int, restock_input: RestockInput, database_connection: Callable
    ) -> dict[str, Any]:
        """Receive supplies: raise the item quantity and log the movement in one transaction."""
        with database_connection() as connection:
            cursor = connection.execute(
                "UPDATE items SET quantity = quantity + ? WHERE id = ?",
                (restock_input.quantity, item_id),
            )
            if cursor.rowcount == 0:
                raise ItemNotFoundError("Item not found")
            movement = StockMovement._record(
                connection, item_id, "RESTOCK", restock_input.quantity, "", restock_input.note
            )
            return {"movement": movement, "item": _fetch_item(connection, item_id)}
