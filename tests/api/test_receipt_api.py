import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.receipt import ReceiptParseResponse, Item
from datetime import datetime
import io
import json
from fastapi import status

client = TestClient(app)

@pytest.fixture
def mock_ocr_service():
    with patch('app.api.endpoints.receipts.OCRService') as mock:
        instance = mock.return_value
        instance.extractTextFromImage.return_value = json.dumps({
            "is_ticket": True,
            "items": [
                {"description": "Café", "quantity": 1, "unit_price": 2.50},
                {"description": "Tostada", "quantity": 2, "unit_price": 3.00}
            ],
            "subtotal": 8.50,
            "tax": 0.85,
            "total": 9.35
        })
        yield instance

@pytest.fixture
def sample_receipt_data():
    items = [
        Item(id=0, name="Café", quantity=1, price=2.50, total_price=2.50),
        Item(id=1, name="Tostada", quantity=2, price=3.00, total_price=6.00)
    ]
    return ReceiptParseResponse(
        receipt_id="test-123",
        items=items,
        subtotal=8.50,
        tax=0.85,
        total=9.35,
        upload_timestamp=datetime.now().isoformat(),
        is_ticket=True,
        error_message=None
    )

@pytest.fixture
def sample_receipt_json(sample_receipt_data):
    return json.dumps({
        "is_ticket": True,
        "items": [
            {"description": "Café", "quantity": 1, "unit_price": 2.50},
            {"description": "Tostada", "quantity": 2, "unit_price": 3.00}
        ],
        "subtotal": 8.50,
        "tax": 0.85,
        "total": 9.35
    })

def test_upload_receipt_success(mock_ocr_service):
    test_image = b"fake image content"
    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "receipt_id" in response_data
    assert len(response_data["items"]) == 2
    assert response_data["subtotal"] == 8.50
    assert response_data["tax"] == 0.85
    assert response_data["total"] == 9.35
    assert response_data["is_ticket"] is True
    assert response_data["error_message"] is None

def test_upload_receipt_no_file():
    response = client.post("/api/v1/receipts/upload")
    assert response.status_code == 422

def test_upload_receipt_invalid_file_type():
    test_file = b"fake content"
    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.txt", test_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "El archivo subido debe ser una imagen" in response.json()["detail"]

def test_split_receipt_success(mock_ocr_service):
    # Subimos el recibo primero
    test_image = b"fake image content"
    upload_response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    assert upload_response.status_code == 200
    receipt_id = upload_response.json()["receipt_id"]
    assignments = {
        "Juan": [1],
        "María": [2]
    }
    response = client.post(
        f"/api/v1/receipts/{receipt_id}/split",
        json={
            "user_item_assignments": assignments
        }
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "total_calculated" in response_data
    assert "shares" in response_data
    assert len(response_data["shares"]) == 2
    for share in response_data["shares"]:
        assert "user_id" in share
        assert "amount_due" in share
        assert "items" in share
        assert "shared_items" in share
        assert isinstance(share["items"], list)
        assert isinstance(share["shared_items"], list)

def test_split_receipt_invalid_assignments(mock_ocr_service):
    # Subimos el recibo primero
    test_image = b"fake image content"
    upload_response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    assert upload_response.status_code == 200
    receipt_id = upload_response.json()["receipt_id"]
    assignments = {
        "Juan": [999]  # ID de item inexistente
    }
    response = client.post(
        f"/api/v1/receipts/{receipt_id}/split",
        json={
            "user_item_assignments": assignments
        }
    )
    assert response.status_code == 400
    assert "Item no encontrado" in response.json()["detail"] 