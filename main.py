"""Create the FastAPI app and connect its inventory routes."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.database import database_connection, initialize_database
from app.models import (
    Category,
    CategoryInput,
    CategoryNotFoundError,
    DuplicateCategoryError,
    InsufficientStockError,
    InventoryError,
    IssueInput,
    Item,
    ItemInput,
    ItemNotFoundError,
    RecordInUseError,
    RestockInput,
    StockMovement,
)

app = FastAPI(title="Supply Room Inventory API")

ERROR_STATUS_CODES = {
    ItemNotFoundError: 404,
    CategoryNotFoundError: 400,
    DuplicateCategoryError: 409,
    RecordInUseError: 409,
    InsufficientStockError: 400,
}


@app.exception_handler(InventoryError)
def handle_inventory_error(request: Request, error: InventoryError):
    status_code = ERROR_STATUS_CODES.get(type(error), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


@app.get("/")
def home():
    return {"message": "Welcome to the Inventory API! Visit /docs to try the API."}


# ---- Categories ----


@app.get("/categories")
def get_categories():
    result = Category.list_categories(database_connection=database_connection)
    return {"categories": result}


@app.get("/categories/{category_id}")
def get_category(category_id: int):
    result = Category.get_category(
        category_id=category_id, database_connection=database_connection
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"category": result}


@app.post("/categories", status_code=201)
def create_category(category: CategoryInput):
    result = Category.create_category(
        category_input=category, database_connection=database_connection
    )
    return {"category": result}


@app.put("/categories/{category_id}")
def edit_category(category_id: int, category: CategoryInput):
    result = Category.update_category(
        category_id=category_id,
        category_input=category,
        database_connection=database_connection,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"category": result}


@app.delete("/categories/{category_id}")
def delete_category(category_id: int):
    deleted = Category.delete_category(
        category_id=category_id, database_connection=database_connection
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}


# ---- Items ----


@app.get("/items")
def get_items(search: str | None = None, category_id: int | None = None):
    result = Item.list_items(
        database_connection=database_connection,
        search=search,
        category_id=category_id,
    )
    return {"items": result}


# Declared before /items/{item_id} so "low-stock" is not parsed as an item ID.
@app.get("/items/low-stock")
def get_low_stock_items(threshold: int = 5):
    result = Item.list_low_stock(
        threshold=threshold, database_connection=database_connection
    )
    return {"items": result}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    result = Item.get_item(
        item_id=item_id, database_connection=database_connection
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": result}


@app.post("/items", status_code=201)
def create_item(item: ItemInput):
    result = Item.create_item(
        item_input=item, database_connection=database_connection
    )
    return {"item": result}


@app.put("/items/{item_id}")
def edit_item(item_id: int, item: ItemInput):
    result = Item.update_item(
        item_id=item_id,
        item_input=item,
        database_connection=database_connection,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": result}


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    deleted = Item.delete_item(
        item_id=item_id, database_connection=database_connection
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


# ---- Stock transactions ----


@app.post("/items/{item_id}/issue", status_code=201)
def issue_stock(item_id: int, issue: IssueInput):
    return StockMovement.issue_stock(
        item_id=item_id, issue_input=issue, database_connection=database_connection
    )


@app.post("/items/{item_id}/restock", status_code=201)
def restock_item(item_id: int, restock: RestockInput):
    return StockMovement.restock_item(
        item_id=item_id, restock_input=restock, database_connection=database_connection
    )


@app.get("/items/{item_id}/movements")
def get_item_movements(item_id: int):
    result = StockMovement.list_for_item(
        item_id=item_id, database_connection=database_connection
    )
    return {"movements": result}


initialize_database()
