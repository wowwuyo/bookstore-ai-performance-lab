"""API acceptance tests for the Week 7 flow."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_openapi() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "/orders" in client.get("/openapi.json").json()["paths"]


def test_inventory_lookup_and_missing_book() -> None:
    with TestClient(app) as client:
        available = client.get("/inventory/1")
        missing = client.get("/inventory/999")

    assert available.status_code == 200
    assert available.json()["book_id"] == 1
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_create_order_reserve_and_prevent_repeat_reservation() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/orders", json={"items": [{"book_id": 1, "quantity": 2}]}
        )
        order_id = created.json()["order_id"]
        before_reservation = client.get("/inventory/1").json()["available_quantity"]
        reserved = client.post(f"/orders/{order_id}/reserve")
        after_reservation = client.get("/inventory/1").json()["available_quantity"]
        repeated = client.post(f"/orders/{order_id}/reserve")

    assert created.status_code == 201
    assert created.json()["status"] == "PENDING"
    assert before_reservation == after_reservation + 2
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "RESERVED"
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "INVALID_ORDER_STATE"


def test_insufficient_multi_item_reservation_does_not_partially_decrement() -> None:
    with TestClient(app) as client:
        before_one = client.get("/inventory/1").json()["available_quantity"]
        before_two = client.get("/inventory/2").json()["available_quantity"]
        created = client.post(
            "/orders",
            json={
                "items": [{"book_id": 1, "quantity": 1}, {"book_id": 2, "quantity": 1}]
            },
        )
        reservation = client.post(f"/orders/{created.json()['order_id']}/reserve")
        after_one = client.get("/inventory/1").json()["available_quantity"]
        after_two = client.get("/inventory/2").json()["available_quantity"]

    assert created.status_code == 201
    assert reservation.status_code == 409
    assert reservation.json()["error"]["code"] == "INSUFFICIENT_INVENTORY"
    assert after_one == before_one
    assert after_two == before_two


def test_order_validation() -> None:
    with TestClient(app) as client:
        empty_items = client.post("/orders", json={"items": []})
        invalid_quantity = client.post(
            "/orders", json={"items": [{"book_id": 1, "quantity": 0}]}
        )

    assert empty_items.status_code == 422
    assert invalid_quantity.status_code == 422
    assert empty_items.json()["error"]["code"] == "VALIDATION_ERROR"
