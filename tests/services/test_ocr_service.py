import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import io
import json

# Helper para imagen de prueba
@pytest.fixture
def sample_image_bytes():
    img = Image.new('RGB', (100, 100), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

@patch('app.services.ocr_service.genai')
def test_init_with_api_key_sets_up_model(mock_genai_module):
    """Prueba que la inicialización con API key configura correctamente el modelo."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    mock_genai_module.configure.assert_called_once_with(api_key="test_api_key")
    mock_genai_module.GenerativeModel.assert_called_once_with('gemini-1.5-flash-latest')
    assert ocr_service.model is mock_model_instance

@patch('app.services.ocr_service.genai')
def test_init_without_api_key_raises_error(mock_genai_module):
    """Prueba que la inicialización sin API key lanza un error."""
    from app.services.ocr_service import OCRService
    with patch('os.getenv', return_value=None):
        with pytest.raises(ValueError) as exc_info:
            OCRService(api_key=None)
        assert "API key de Gemini no encontrada" in str(exc_info.value)
    mock_genai_module.configure.assert_not_called()

@patch('app.services.ocr_service.genai')
def test_extractTextFromImage_valid_ticket_returns_json(mock_genai_module, sample_image_bytes):
    """Prueba que la extracción de texto de un ticket válido devuelve JSON correcto."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    expected_json = {
        "is_ticket": True,
        "items": [
            {"description": "Café", "quantity": 1, "unit_price": 2.50},
            {"description": "Tostada", "quantity": 2, "unit_price": 3.00}
        ],
        "subtotal": 8.50,
        "tax": 0.85,
        "total": 9.35
    }
    
    mock_api_response = MagicMock()
    mock_api_response.parts = [MagicMock()]
    mock_api_response.parts[0].text = json.dumps(expected_json)
    mock_model_instance.generate_content.return_value = mock_api_response
    
    resultado = ocr_service.extractTextFromImage(sample_image_bytes)
    resultado_json = json.loads(resultado)
    
    assert resultado_json["is_ticket"] is True
    assert len(resultado_json["items"]) == 2
    assert resultado_json["items"][0]["description"] == "Café"
    assert resultado_json["items"][1]["description"] == "Tostada"
    assert resultado_json["subtotal"] == 8.50
    assert resultado_json["tax"] == 0.85
    assert resultado_json["total"] == 9.35
    mock_model_instance.generate_content.assert_called_once()

@patch('app.services.ocr_service.genai')
def test_extractTextFromImage_not_ticket_returns_error_json(mock_genai_module, sample_image_bytes):
    """Prueba que la extracción de texto de una imagen que no es ticket devuelve JSON de error."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    expected_json = {
        "is_ticket": False,
        "error_message": "La imagen que has subido parece ser una foto personal. Por favor, sube una imagen de un ticket de compra o factura válido.",
        "detected_content": "Foto de una persona"
    }
    
    mock_api_response = MagicMock()
    mock_api_response.parts = [MagicMock()]
    mock_api_response.parts[0].text = json.dumps(expected_json)
    mock_model_instance.generate_content.return_value = mock_api_response
    
    resultado = ocr_service.extractTextFromImage(sample_image_bytes)
    resultado_json = json.loads(resultado)
    
    assert resultado_json["is_ticket"] is False
    assert "error_message" in resultado_json
    assert "detected_content" in resultado_json
    mock_model_instance.generate_content.assert_called_once()

@patch('app.services.ocr_service.genai')
def test_extractTextFromImage_empty_response_returns_empty_string(mock_genai_module, sample_image_bytes):
    """Prueba que la extracción de texto con respuesta vacía devuelve string vacío."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    mock_api_response = MagicMock()
    mock_api_response.parts = [] # Simula una respuesta sin partes de texto
    mock_model_instance.generate_content.return_value = mock_api_response
    
    resultado = ocr_service.extractTextFromImage(sample_image_bytes)
    assert resultado == ""
    mock_model_instance.generate_content.assert_called_once()

@patch('app.services.ocr_service.genai')
def test_preprocessImageForOcr_valid_bytes_returns_image(mock_genai_module, sample_image_bytes):
    """Prueba que el preprocesamiento de imagen válida devuelve objeto Image."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    resultado = ocr_service._preprocessImageForOcr(sample_image_bytes)
    assert isinstance(resultado, Image.Image)
    assert resultado.mode == 'RGB'

@patch('app.services.ocr_service.genai')
def test_preprocessImageForOcr_invalid_bytes_raises_error(mock_genai_module):
    """Prueba que el preprocesamiento de bytes inválidos lanza error."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    invalid_bytes = b"not an image"
    with pytest.raises(ValueError) as exc_info:
        ocr_service._preprocessImageForOcr(invalid_bytes)
    assert "Los bytes de la imagen no son válidos" in str(exc_info.value)

@patch('app.services.ocr_service.genai')
def test_extractTextFromImage_handles_markdown_json(mock_genai_module, sample_image_bytes):
    """Prueba que la extracción de texto maneja correctamente JSON con formato markdown."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    expected_json = {
        "is_ticket": True,
        "items": [
            {"description": "Café", "quantity": 1, "unit_price": 2.50}
        ],
        "total": 2.50
    }
    
    mock_api_response = MagicMock()
    mock_api_response.parts = [MagicMock()]
    mock_api_response.parts[0].text = f"```json\n{json.dumps(expected_json)}\n```"
    mock_model_instance.generate_content.return_value = mock_api_response
    
    resultado = ocr_service.extractTextFromImage(sample_image_bytes)
    resultado_json = json.loads(resultado)
    
    assert resultado_json["is_ticket"] is True
    assert len(resultado_json["items"]) == 1
    assert resultado_json["items"][0]["description"] == "Café"
    assert resultado_json["total"] == 2.50
    mock_model_instance.generate_content.assert_called_once()

@patch('app.services.ocr_service.genai')
def test_extractTextFromImage_invalid_json_raises_error(mock_genai_module, sample_image_bytes):
    """Prueba que la extracción de texto con JSON inválido lanza error."""
    from app.services.ocr_service import OCRService
    
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance
    
    ocr_service = OCRService(api_key="test_api_key")
    
    mock_api_response = MagicMock()
    mock_api_response.parts = [MagicMock()]
    mock_api_response.parts[0].text = "invalid json" # JSON inválido
    mock_model_instance.generate_content.return_value = mock_api_response
    
    with pytest.raises(RuntimeError) as exc_info:
        ocr_service.extractTextFromImage(sample_image_bytes)
    assert "La respuesta del modelo no es un JSON válido" in str(exc_info.value)
    mock_model_instance.generate_content.assert_called_once() 