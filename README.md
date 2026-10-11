# Supply Room Inventory System (FastAPI + SQLite)

## Problem and purpose

Schools and small offices often track supplies on paper or in a single spreadsheet. Stock counts drift,
nobody records who took what, and shortages are noticed only when something runs out. This system gives
the stockroom staff one place to keep items by category, issue supplies to people, record deliveries, and
see which items are running low. Every change to stock is logged, so the quantity on hand can always be
explained by the movement history.

Intended users: stockroom staff / property custodians (they issue and restock supplies) and the
administrators who review stock levels and history.

## Run it on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> to try the API.

If you have an `inventory.db` from the earlier single-table version, delete it first. The new `category_id`
column cannot be added by `CREATE TABLE IF NOT EXISTS`, and the file is regenerated on startup.

## Database design

| Table | Purpose | Keys |
|---|---|---|
| `categories` | Groups of items (unique name) | PK `id` |
| `items` | Supplies and quantity on hand | PK `id`, FK `category_id` -> `categories.id` |
| `stock_movements` | Log of every issue and restock | PK `id`, FK `item_id` -> `items.id` |

Relationships: one category has many items; one item has many stock movements. Foreign keys use
`ON DELETE RESTRICT`, so a category with items, or an item with history, cannot be deleted. SQLite only
enforces foreign keys when `PRAGMA foreign_keys = ON` is set, which `database_connection()` does for every
connection. `CHECK` constraints keep quantity and price non-negative and movement quantity positive.

## Transactional workflow

`POST /items/{id}/issue` (issue supplies to a person) does three things in one database transaction:

1. confirm the item exists,
2. lower `items.quantity` with `UPDATE ... WHERE quantity >= requested` (the stock check and the decrement
   are a single atomic statement),
3. insert an `ISSUE` row in `stock_movements`.

If stock is insufficient, nothing is written and the API returns `400`. `POST /items/{id}/restock` is the
reverse (a delivery) and logs a `RESTOCK` row. `database_connection()` commits on success and rolls back on
any exception, so the quantity and the log can never disagree.

## Object-oriented design

- Pydantic classes (`ItemInput`, `CategoryInput`, `IssueInput`, `RestockInput`) validate input.
- `Category`, `Item`, and `StockMovement` each own the database operations for their table.
- Inheritance: `Item(ItemInput)` and `Category(CategoryInput)` extend their input schemas with an `id`.
- Domain errors (`ItemNotFoundError`, `InsufficientStockError`, ...) derive from `InventoryError`; one
  exception handler in `main.py` turns them into HTTP responses, which keeps routes thin.
- The database connection is injected into each method, so the models do not depend on a global.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET / POST | `/categories` | List / create category |
| GET / PUT / DELETE | `/categories/{id}` | Read / update / delete category |
| GET | `/items?search=&category_id=` | List and search items |
| GET | `/items/low-stock?threshold=5` | Items at or below the threshold |
| POST | `/items` | Create item (optional `category_id`) |
| GET / PUT / DELETE | `/items/{id}` | Read / update / delete item |
| POST | `/items/{id}/issue` | Issue supplies (transaction) |
| POST | `/items/{id}/restock` | Receive supplies (transaction) |
| GET | `/items/{id}/movements` | Movement history, newest first |

Example issue request body:

```json
{ "quantity": 3, "issued_to": "Ms. Cruz", "note": "Grade 7 classroom" }
```

## Project structure

- `main.py` creates the app, defines the routes, and maps domain errors to HTTP responses.
- `app/database.py` opens SQLite connections and creates the three tables.
- `app/models.py` holds the schemas, domain errors, and database operations.
- `tests/test_api.py` has API tests (`pip install pytest httpx`, then `python -m pytest`).
- `inventory.db` is created automatically on first run and is git-ignored.
## Status
Project updated.