import google.generativeai as genai
from PIL import Image
import io
# import cv2 # Ya no es necesario para el preprocesamiento si Gemini lo maneja bien
# import numpy as np # Ya no es necesario
import os
import json
from typing import Optional, Dict, Any

# ¡¡¡ADVERTENCIA DE SEGURIDAD!!!
# Es MUY RECOMENDABLE cargar la API key desde una variable de entorno en producción.
# Ejemplo: API_KEY = os.getenv("GEMINI_API_KEY")
# No la dejes hardcodeada así, especialmente si el código es compartido o público.

class OCRService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el servicio OCR usando la API de Gemini.
        
        Args:
            api_key: Clave API opcional. Si no se proporciona, se intentará obtener de GEMINI_API_KEY.
        
        Raises:
            ValueError: Si no se puede encontrar una API key válida.
            RuntimeError: Si hay un error al configurar la API de Gemini.
        """
        self._configure_api(api_key)
        self._initialize_model()

    def _configure_api(self, api_key: Optional[str]) -> None:
        """Configura la API key de Gemini."""
        retrieved_env_api_key = os.getenv("GEMINI_API_KEY")
        resolved_api_key = api_key or retrieved_env_api_key
        
        if not resolved_api_key:
            raise ValueError("API key de Gemini no encontrada. Configúrala como variable de entorno GEMINI_API_KEY o pásala al constructor.")
        
        try:
            genai.configure(api_key=resolved_api_key)
        except Exception as e:
            raise RuntimeError(f"Error al configurar Gemini API: {e}") from e

    def _initialize_model(self) -> None:
        """Inicializa el modelo de Gemini."""
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        except Exception as e:
            raise RuntimeError(f"Error al inicializar el modelo de Gemini: {e}") from e

    def _preprocessImageForOcr(self, image_bytes: bytes) -> Image.Image:
        """
        Preprocesa la imagen para OCR.
        
        Args:
            image_bytes: Bytes de la imagen a procesar.
            
        Returns:
            Image.Image: Imagen procesada.
            
        Raises:
            ValueError: Si los bytes de la imagen no son válidos.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return image
        except Exception as e:
            raise ValueError(f"Los bytes de la imagen no son válidos: {e}") from e

    def _clean_json_response(self, text: str) -> str:
        """
        Limpia la respuesta JSON del modelo.
        
        Args:
            text: Texto a limpiar.
            
        Returns:
            str: Texto limpio.
        """
        cleaned_text = text.strip()
        
        # Eliminar marcadores de código markdown si existen
        if cleaned_text.startswith("```json"):
            start_index = cleaned_text.find('{')
            if start_index != -1:
                cleaned_text = cleaned_text[start_index:]
        
        if cleaned_text.endswith("```"):
            end_index = cleaned_text.rfind('}')
            if end_index != -1:
                cleaned_text = cleaned_text[:end_index + 1]
        
        return cleaned_text.strip()

    def extractTextFromImage(self, image_bytes: bytes, language: str = 'spa') -> str:
        """
        Extrae texto de una imagen usando la API de Gemini.
        
        Args:
            image_bytes: Bytes de la imagen a procesar.
            language: Idioma del ticket (por defecto 'spa' para español).
            
        Returns:
            str: JSON con la información extraída del ticket.
            
        Raises:
            ValueError: Si los bytes de la imagen no son válidos.
            RuntimeError: Si hay un error al procesar la imagen.
        """
        try:
            pil_image = self._preprocessImageForOcr(image_bytes)
            
            prompt = self._generate_prompt(language)
            response = self.model.generate_content([prompt, pil_image])
            
            if not response.parts or not response.parts[0].text:
                return ""
            
            extracted_text = response.parts[0].text
            cleaned_text = self._clean_json_response(extracted_text)
            
            # Validar que el texto limpio es un JSON válido
            try:
                json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"La respuesta del modelo no es un JSON válido: {e}")
            
            return cleaned_text
            
        except Exception as e:
            if isinstance(e, (ValueError, RuntimeError)):
                raise
            raise RuntimeError(f"Error al procesar imagen con Gemini: {e}") from e

    def _generate_prompt(self, language: str) -> str:
        """Genera el prompt para el modelo."""
        return f"""
PRIMERO: Analiza cuidadosamente la imagen para determinar si es un ticket de compra, factura o recibo.

Si la imagen NO es un ticket de compra/factura/recibo (por ejemplo: es una foto personal, paisaje, documento diferente, pantalla, texto general, etc.), devuelve ÚNICAMENTE este JSON:
{{
  "is_ticket": false,
  "error_message": "La imagen que has subido parece ser [DESCRIBE_QUE_TIPO_DE_IMAGEN_ES]. Por favor, sube una imagen de un ticket de compra o factura válido.",
  "detected_content": "[breve descripción de lo que se ve en la imagen]"
}}

Si la imagen SÍ es un ticket de compra/factura/recibo, extrae la información de cada artículo (descripción, cantidad y precio unitario), 
así como el subtotal, los impuestos (si se especifican) y el importe total final. 
El idioma principal del ticket es '{language if language else 'español'}'
Devuelve la información ÚNICAMENTE en formato JSON válido, estructurado de la siguiente manera:
{{
  "is_ticket": true,
  "items": [
    {{"description": "nombre del artículo", "quantity": numero, "unit_price": numero}},
    // ... más artículos
  ],
  "subtotal": numero_o_null,
  "tax": numero_o_null,
  "total": numero_o_null
}}

INSTRUCCIONES IMPORTANTES:
- Asegúrate de que todos los valores numéricos sean números (float o integer), no strings
- Utiliza un punto como separador decimal
- Si una cantidad no es explícita, asume 1
- Si el subtotal o los impuestos no se pueden determinar claramente, usa null para sus valores
- No incluyas ningún texto explicativo adicional fuera del objeto JSON
- Siempre incluye el campo "is_ticket" para indicar si la imagen es un ticket válido
"""

# Ejemplo de uso (no se ejecutará directamente aquí):
# if __name__ == '__main__':
#     # Para probar, asegúrate de que la variable de entorno GEMINI_API_KEY está configurada
#     # o pasa la clave directamente: ocr_service = OCRService(api_key="TU_API_KEY_AQUI")
#     ocr_service = OCRService() 
#     try:
#         # Reemplaza "ruta/a/tu/ticket.png" con una ruta real a una imagen
#         with open("ruta/a/tu/ticket.png", "rb") as f:
#             image_bytes = f.read()
#         text = ocr_service.extractTextFromImage(image_bytes, language='spa')
#         print("\n--- Texto extraído por Gemini ---")
#         print(text)
#     except FileNotFoundError:
#         print("Archivo de imagen de ejemplo no encontrado.")
#     except RuntimeError as e:
#         print(f"Error de OCR con Gemini: {e}")
#     except ValueError as e:
#         print(f"Error de configuración o datos: {e}") 