import pytest
from fastapi.testclient import TestClient
from typing import Generator

# Importar la app principal de FastAPI
# Asegúrate de que la estructura de tu proyecto permita esta importación.
# Si tests/ está al mismo nivel que app/, puede que necesites ajustar PYTHONPATH
# o la forma en que se importa la app. Por ahora, asumimos que funciona.
from app.main import app 

# Fixture para el cliente de prueba de FastAPI
@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """
    Genera un cliente de prueba para la aplicación FastAPI.
    Este cliente permite hacer peticiones HTTP a la app sin necesidad de un servidor real.
    El scope es "module" para que el cliente se cree una vez por módulo de pruebas.
    """
    with TestClient(app) as test_client:
        yield test_client

# Fixture para los servicios (opcional, pero útil si quieres mockearlos)
# Ejemplo de cómo podrías mockear el OCRService si fuera necesario.
# from app.services.ocr_service import OCRService
# from unittest.mock import MagicMock
#
# @pytest.fixture
# def mock_ocr_service() -> MagicMock:
# mock = MagicMock(spec=OCRService)
# mock.extract_text_from_image.return_value = "Texto de prueba del OCR mockeado"
# return mock
#
# Si necesitas sobreescribir dependencias en tus tests, puedes hacerlo así:
# from app.api.endpoints.receipts import get_ocr_service
# app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service

# Podrías añadir más fixtures aquí, por ejemplo:
# - Datos de prueba para items o recibos.
# - Funciones helper para crear datos de prueba comunes. 