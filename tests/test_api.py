"""API tests. Run from the project root with: python -m pytest

Requires: pip install pytest httpx
"""

import pytest
from fastapi.testclient import TestClient

import app.database as database
from main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "test.db")
    database.initialize_database()
    return TestClient(app)


def make_item(client, quantity=10, category_id=None):
    body = {"name": "Notebook", "description": "A4", "quantity": quantity, "price": 49.5}
    if category_id is not None:
        body["category_id"] = category_id
    return client.post("/items", json=body).json()["item"]


def test_item_crud_and_search(client):
    item = make_item(client)
    assert client.get(f"/items/{item['id']}").status_code == 200
    assert len(client.get("/items", params={"search": "note"}).json()["items"]) == 1
    updated = client.put(f"/items/{item['id']}", json={**item, "quantity": 3}).json()["item"]
    assert updated["quantity"] == 3
    assert client.delete(f"/items/{item['id']}").status_code == 200
    assert client.get(f"/items/{item['id']}").status_code == 404


def test_item_requires_existing_category(client):
    response = client.post(
        "/items",
        json={"name": "X", "quantity": 1, "price": 1, "category_id": 999},
    )
    assert response.status_code == 400


def test_issue_stock_is_atomic(client):
    item = make_item(client, quantity=5)
    ok = client.post(f"/items/{item['id']}/issue", json={"quantity": 3, "issued_to": "Ms. Cruz"})
    assert ok.status_code == 201
    assert ok.json()["item"]["quantity"] == 2
    too_many = client.post(f"/items/{item['id']}/issue", json={"quantity": 3, "issued_to": "Ms. Cruz"})
    assert too_many.status_code == 400
    assert client.get(f"/items/{item['id']}").json()["item"]["quantity"] == 2
    assert len(client.get(f"/items/{item['id']}/movements").json()["movements"]) == 1


def test_restock_and_low_stock(client):
    item = make_item(client, quantity=1)
    assert [i["id"] for i in client.get("/items/low-stock").json()["items"]] == [item["id"]]
    client.post(f"/items/{item['id']}/restock", json={"quantity": 20})
    assert client.get("/items/low-stock").json()["items"] == []


def test_foreign_keys_block_deletes(client):
    category = client.post("/categories", json={"name": "Stationery"}).json()["category"]
    item = make_item(client, category_id=category["id"])
    assert client.delete(f"/categories/{category['id']}").status_code == 409
    client.post(f"/items/{item['id']}/issue", json={"quantity": 1, "issued_to": "Admin"})
    assert client.delete(f"/items/{item['id']}").status_code == 409
