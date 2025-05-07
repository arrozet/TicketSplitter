import pytest
from fastapi.testclient import TestClient
from fastapi import status # Para códigos de estado HTTP
import io

# Asumimos que processed_receipts_db está en app.api.endpoints.receipts
# Esto es para poder limpiarlo o inspeccionarlo entre tests si es necesario.
# Sin embargo, es mejor no depender de la implementación interna de esta manera para tests puramente de API.
# Por ahora, lo usaremos para obtener un ID válido para los tests de split.
from app.api.endpoints.receipts import processed_receipts_db 

# --- Tests para el endpoint de Health Check ---
def test_health_check(client: TestClient):
    """Prueba que el endpoint de health check funcione correctamente."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

# --- Tests para el endpoint de subida de tickets (/upload) ---

@pytest.fixture
def mock_ocr_parser_services(mocker): # mocker es una fixture de pytest-mock
    """Mockea los servicios de OCR y Parser para controlar sus salidas."""
    mock_ocr = mocker.patch('app.services.ocr_service.OCRService.extract_text_from_image')
    mock_ocr.return_value = "TEXTO EXTRAIDO DE PRUEBA\nITEM1 10.00\nITEM2 5.50\nTOTAL 15.50"

    mock_parser = mocker.patch('app.services.parser_service.ParserService.parse_text_to_items')
    mock_parser.return_value = {
        "items": [
            {"id": 1, "name": "ITEM1", "quantity": 1, "price": 10.00, "total_price": 10.00},
            {"id": 2, "name": "ITEM2", "quantity": 1, "price": 5.50, "total_price": 5.50}
        ],
        "subtotal": None, # Podríamos añadir valores si quisiéramos probarlos
        "tax": None,
        "total": 15.50,
        "raw_text": "TEXTO EXTRAIDO DE PRUEBA\nITEM1 10.00\nITEM2 5.50\nTOTAL 15.50"
    }
    return mock_ocr, mock_parser

def test_upload_receipt_image_success(client: TestClient, mock_ocr_parser_services):
    """Prueba la subida exitosa de una imagen de ticket."""
    # Simular un archivo de imagen en memoria
    image_content = b"simulacro de bytes de imagen png"
    file_to_upload = {"file": ("test_receipt.png", io.BytesIO(image_content), "image/png")}
    
    response = client.post("/api/v1/receipts/upload", files=file_to_upload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "receipt_id" in data
    assert data["filename"] == "test_receipt.png"
    assert "upload_timestamp" in data
    assert "items" in data
    assert len(data["items"]) == 2 # Basado en el mock_parser
    assert data["items"][0]["name"] == "ITEM1"
    assert data["total"] == 15.50
    assert data["raw_text"] is not None

    # Guardar el ID para otros tests (no ideal, pero funciona para este ejemplo simple)
    # Un mejor enfoque sería que los tests que dependen de un ID lo creen ellos mismos.
    pytest.receipt_id_for_test = data["receipt_id"]

def test_upload_receipt_not_an_image(client: TestClient):
    """Prueba subir un archivo que no es una imagen."""
    text_content = b"esto no es una imagen"
    file_to_upload = {"file": ("test_not_image.txt", io.BytesIO(text_content), "text/plain")}
    
    response = client.post("/api/v1/receipts/upload", files=file_to_upload)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "El archivo subido debe ser una imagen" in response.json()["detail"]

# --- Test para obtener datos de un ticket (/receipt_id) ---
def test_get_receipt_data_found(client: TestClient):
    """Prueba obtener datos de un ticket existente."""
    # Este test depende de que test_upload_receipt_image_success se haya ejecutado
    # y haya guardado un receipt_id. Esto no es ideal para tests aislados.
    # En un setup más robusto, se crearía un ticket aquí directamente si es necesario.
    receipt_id = getattr(pytest, 'receipt_id_for_test', None)
    assert receipt_id is not None, "El test de subida debe ejecutarse primero y crear un receipt_id"

    response = client.get(f"/api/v1/receipts/{receipt_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["receipt_id"] == receipt_id
    assert len(data["items"]) > 0 # Asumiendo que el test de subida pobló items

def test_get_receipt_data_not_found(client: TestClient):
    """Prueba obtener datos de un ticket con un ID inexistente."""
    response = client.get("/api/v1/receipts/non_existent_id_123")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Ticket no encontrado" in response.json()["detail"]

# --- Tests para dividir un ticket (/{receipt_id}/split) ---
def test_split_receipt_success(client: TestClient):
    """Prueba dividir un ticket exitosamente."""
    receipt_id = getattr(pytest, 'receipt_id_for_test', None)
    assert receipt_id is not None, "El test de subida debe ejecutarse primero y crear un receipt_id"

    # Obtener los IDs de los items del ticket creado en el test de subida
    # Esto es frágil. Sería mejor tener items con IDs conocidos o mockear la respuesta de get_receipt_data.
    # Por ahora, asumimos que los items mockeados tienen IDs 1 y 2.
    
    split_payload = {
        "user_item_assignments": {
            "Alice": [1],       # Item con ID 1 mockeado (precio 10.00)
            "Bob": [2]        # Item con ID 2 mockeado (precio 5.50)
        }
    }
    response = client.post(f"/api/v1/receipts/{receipt_id}/split", json=split_payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_calculated" in data
    assert len(data["shares"]) == 2
    
    alice_share = next(s for s in data["shares"] if s["user_id"] == "Alice")
    bob_share = next(s for s in data["shares"] if s["user_id"] == "Bob")
    
    assert alice_share["amount_due"] == 10.00 # Basado en el mock de parser
    assert bob_share["amount_due"] == 5.50   # Basado en el mock de parser
    assert data["total_calculated"] == 15.50

def test_split_receipt_no_assignments(client: TestClient):
    """Prueba dividir un ticket sin proporcionar asignaciones."""
    receipt_id = getattr(pytest, 'receipt_id_for_test', None)
    assert receipt_id is not None, "El test de subida debe ejecutarse primero y crear un receipt_id"
    
    split_payload = {"user_item_assignments": {}}
    response = client.post(f"/api/v1/receipts/{receipt_id}/split", json=split_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No se proporcionaron asignaciones" in response.json()["detail"]

def test_split_receipt_ticket_not_found(client: TestClient):
    """Prueba dividir un ticket que no existe."""
    split_payload = {"user_item_assignments": {"Alice": [1]}}
    response = client.post("/api/v1/receipts/non_existent_id_456/split", json=split_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Ticket no encontrado para dividir" in response.json()["detail"]

# Consideraciones para mejorar estos tests:
# 1. Evitar la dependencia secuencial de tests (ej. `pytest.receipt_id_for_test`).
#    Cada test debería ser lo más independiente posible, creando sus propios pre-requisitos si es necesario,
#    o usando fixtures que preparen el estado. Por ejemplo, un fixture que cree un ticket procesado.
# 2. Mockear dependencias de manera más granular cuando se prueban unidades específicas.
#    Para tests de API, mockear servicios externos (OCR, Parser) es bueno para aislar el endpoint.
# 3. Probar más casos límite y de error para los endpoints. 