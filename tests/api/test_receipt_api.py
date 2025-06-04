import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.receipt import ReceiptParseResponse, Item
from datetime import datetime
import io
import json
from fastapi import status

# Cliente de prueba de FastAPI que simula peticiones HTTP
client = TestClient(app)

@pytest.fixture
def mock_ocr_service():
    """
    Fixture que simula el servicio OCR.
    Reemplaza la clase OCRService real por un mock que devuelve datos predefinidos.
    Esto evita hacer llamadas reales al servicio de OCR durante las pruebas.
    """
    with patch('app.api.endpoints.receipts.OCRService') as mock:
        instance = mock.return_value
        # Simula la respuesta del OCR con datos de un recibo de ejemplo
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
    """
    Fixture que proporciona datos de ejemplo de un recibo.
    Útil para pruebas que necesitan datos de recibo predefinidos.
    """
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
    """
    Fixture que convierte los datos del recibo de ejemplo a formato JSON.
    Útil para pruebas que necesitan datos en formato JSON.
    """
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

def test_uploadReceipt_validImage_returnsReceiptData(mock_ocr_service):
    """
    Prueba la subida exitosa de una imagen de recibo.
    Verifica que el endpoint /upload procesa correctamente la imagen y devuelve los datos del recibo.
    """
    # Arrange
    test_image = b"fake image content"
    
    # Act
    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "receipt_id" in response_data
    assert len(response_data["items"]) == 2
    assert response_data["subtotal"] == 8.50
    assert response_data["tax"] == 0.85
    assert response_data["total"] == 9.35
    assert response_data["is_ticket"] is True
    assert response_data["error_message"] is None

def test_uploadReceipt_noFile_returnsValidationError():
    """
    Prueba el comportamiento cuando se intenta subir un recibo sin archivo.
    Verifica que FastAPI devuelve un error de validación (422).
    """
    # Arrange
    # No se necesita preparación especial
    
    # Act
    response = client.post("/api/v1/receipts/upload")
    
    # Assert
    assert response.status_code == 422

def test_uploadReceipt_invalidFileType_returnsBadRequest():
    """
    Prueba el comportamiento cuando se intenta subir un archivo que no es una imagen.
    Verifica que la API devuelve un error 400 con el mensaje apropiado.
    """
    # Arrange
    test_file = b"fake content"
    
    # Act
    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.txt", test_file, "text/plain")}
    )
    
    # Assert
    assert response.status_code == 400
    assert "El archivo subido debe ser una imagen" in response.json()["detail"]

def test_splitReceipt_validAssignments_returnsSplitData(mock_ocr_service):
    """
    Prueba la división exitosa de un recibo entre usuarios.
    Verifica que el endpoint /split calcula correctamente las participaciones.
    """
    # Arrange
    test_image = b"fake image content"
    upload_response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    receipt_id = upload_response.json()["receipt_id"]
    assignments = {
        "Juan": [1],
        "María": [2]
    }
    
    # Act
    response = client.post(
        f"/api/v1/receipts/{receipt_id}/split",
        json={"user_item_assignments": assignments}
    )
    
    # Assert
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

def test_splitReceipt_invalidItemId_returnsBadRequest(mock_ocr_service):
    """
    Prueba el comportamiento cuando se intenta asignar un item inexistente.
    Verifica que la API devuelve un error 400 con el mensaje apropiado.
    """
    # Arrange
    test_image = b"fake image content"
    upload_response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    receipt_id = upload_response.json()["receipt_id"]
    assignments = {
        "Juan": [999]  # ID de item inexistente
    }
    
    # Act
    response = client.post(
        f"/api/v1/receipts/{receipt_id}/split",
        json={"user_item_assignments": assignments}
    )
    
    # Assert
    assert response.status_code == 400
    assert "Item no encontrado" in response.json()["detail"]

def test_getReceipt_validId_returnsReceiptData(mock_ocr_service):
    """
    Prueba la obtención exitosa de un recibo por su ID.
    Verifica que el endpoint GET devuelve los datos correctos del recibo.
    """
    # Arrange
    test_image = b"fake image content"
    upload_response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("test.jpg", test_image, "image/jpeg")}
    )
    receipt_id = upload_response.json()["receipt_id"]
    
    # Act
    response = client.get(f"/api/v1/receipts/{receipt_id}")
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["receipt_id"] == receipt_id
    assert len(response_data["items"]) == 2
    assert response_data["subtotal"] == 8.50

def test_getReceipt_invalidId_returnsNotFound():
    """
    Prueba el comportamiento cuando se intenta obtener un recibo con ID inexistente.
    Verifica que la API devuelve un error 404 con el mensaje apropiado.
    """
    # Arrange
    # No se necesita preparación especial
    
    # Act
    response = client.get("/api/v1/receipts/non-existent-id")
    
    # Assert
    assert response.status_code == 404
    assert "Ticket no encontrado" in response.json()["detail"] 