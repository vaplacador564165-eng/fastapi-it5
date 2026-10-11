# Beginner FastAPI + SQLite Inventory System

This project keeps the original starter project's structure and changes the example from students to inventory items. It uses FastAPI for the API, Pydantic for input validation, and SQLite to store item records.

## Run it on Windows

From this folder, create and activate a virtual environment, install dependencies, and start the API:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> to try the API in the interactive documentation.

## Project structure

- `main.py` creates the FastAPI app and defines the routes.
- `app/database.py` opens SQLite connections and creates the inventory table.
- `app/models.py` defines the Pydantic item data classes and database operations.
- `inventory.db` is created automatically when the app first runs.
- `requirements.txt` lists the Python dependencies.

## Item fields

Each item has an automatically generated `id`, a `name`, a `description`, a `quantity`, and a `price`. Quantity and price cannot be negative. The API validates input before saving it to the database.

Example request body:

```json
{
  "name": "Notebook",
  "description": "A4 ruled notebook",
  "quantity": 25,
  "price": 49.5
}
```

## API endpoints

- `GET /` returns a welcome message.
- `GET /items` lists all inventory items.
- `GET /items/{item_id}` gets one item by ID.
- `POST /items` adds an item.
- `PUT /items/{item_id}` updates an existing item.
- `DELETE /items/{item_id}` deletes an item.

The API returns a `404` response when an item ID does not exist. Try the endpoints in `/docs`.

## Database notes

The application creates `inventory.db` and the `items` table automatically. SQL queries use `?` placeholders to safely pass values into queries. The previous `students.db` file is not used by this inventory version.
