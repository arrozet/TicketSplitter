import google.generativeai as genai
from PIL import Image
import io
# import cv2 # Ya no es necesario para el preprocesamiento si Gemini lo maneja bien
# import numpy as np # Ya no es necesario
import os

# ¡¡¡ADVERTENCIA DE SEGURIDAD!!!
# Es MUY RECOMENDABLE cargar la API key desde una variable de entorno en producción.
# Ejemplo: API_KEY = os.getenv("GEMINI_API_KEY")
# No la dejes hardcodeada así, especialmente si el código es compartido o público.

class OCRService:
    def __init__(self, api_key: str = None):
        """
        Inicializa el servicio OCR usando la API de Gemini.
        """
        # Intentar obtener la API key de la variable de entorno
        retrieved_env_api_key = os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: Valor de GEMINI_API_KEY obtenido de os.getenv(): '{retrieved_env_api_key}'") # <-- LÍNEA DE PRUEBA

        resolved_api_key = api_key or retrieved_env_api_key
        
        if not resolved_api_key:
            print("ERROR: No se pudo resolver la API key de Gemini. Ni pasada como argumento ni encontrada en GEMINI_API_KEY.")
            raise ValueError("API key de Gemini no encontrada. Configúrala como variable de entorno GEMINI_API_KEY o pásala al constructor.")
        
        try:
            genai.configure(api_key=resolved_api_key)
            # Usaremos gemini-pro-vision ya que necesitamos procesar imágenes
            # self.model = genai.GenerativeModel('gemini-pro-vision') # Modelo deprecado
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest') # Modelo actualizado
            print(f"DEBUG: Servicio OCR configurado con Gemini API y modelo 'gemini-1.5-flash-latest'.")
        except Exception as e:
            print(f"Error al configurar Gemini API: {e}")
            raise RuntimeError(f"No se pudo configurar Gemini API: {e}") from e

    def _preprocess_image_for_ocr(self, image_bytes: bytes) -> Image.Image:
        """
        El preprocesamiento podría no ser tan necesario con Gemini, 
        pero mantenemos la función por si se quiere añadir algo en el futuro.
        Por ahora, solo convierte bytes a objeto PIL.Image.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Podríamos convertir a RGB para asegurar compatibilidad si es necesario.
            # if image.mode != 'RGB':
            #     image = image.convert('RGB')
            return image
        except Exception as e:
            print(f"Error al cargar la imagen para Gemini: {e}")
            raise ValueError(f"Los bytes de la imagen no son válidos: {e}") from e

    def extract_text_from_image(self, image_bytes: bytes, language: str = 'spa') -> str:
        """
        Extrae texto de una imagen usando la API de Gemini.
        El parámetro 'language' es menos directo que con Tesseract, pero podemos guiar al modelo.
        """
        print(f"DEBUG: Iniciando extracción de texto con Gemini Vision para imagen de {len(image_bytes)} bytes.")
        try:
            pil_image = self._preprocess_image_for_ocr(image_bytes)
            
            # El prompt puede ser ajustado para mejorar los resultados.
            # Incluir el idioma en el prompt puede ayudar.
            prompt = f"""
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
            
            # Preparar la entrada para el modelo (imagen + prompt)
            # La API espera una lista de "partes"
            response = self.model.generate_content([prompt, pil_image])
            
            # Asegurarse de que hay texto en la respuesta
            if response.parts and response.parts[0].text:
                extracted_text = response.parts[0].text
                print(f"DEBUG: Texto bruto devuelto por Gemini: {extracted_text[:300]}...")

                # Limpiar el texto si está envuelto en bloques de código markdown JSON
                cleaned_text = extracted_text.strip()
                if cleaned_text.startswith("```json") or cleaned_text.startswith("```jsoni") : # Considerar la errata
                    # Encontrar el inicio del JSON real después del ```json\n
                    start_index = cleaned_text.find('{')
                    if start_index != -1:
                        cleaned_text = cleaned_text[start_index:]
                
                # Buscar el final del JSON antes del ``` final
                if cleaned_text.endswith("```"):
                    end_index = cleaned_text.rfind('}')
                    if end_index != -1:
                        cleaned_text = cleaned_text[:end_index + 1]
                
                cleaned_text = cleaned_text.strip() # Una limpieza final por si acaso

                print(f"DEBUG: Texto limpiado (esperando JSON): {cleaned_text[:300]}...")
                return cleaned_text
            else:
                # Esto podría ocurrir si la imagen no tiene texto o Gemini no lo encuentra.
                # O si la respuesta no es lo que esperamos (ej. bloqueada por seguridad).
                # Revisar response.prompt_feedback puede dar más información.
                feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else "No feedback available"
                print(f"ADVERTENCIA: Gemini no devolvió texto. Feedback: {feedback}")
                return "" # Devolver string vacío si no se extrae texto

        except Exception as e:
            print(f"Error durante la extracción de texto con Gemini API: {e}")
            # En producción, es mejor loggear esto detalladamente.
            raise RuntimeError(f"Error al procesar imagen con Gemini: {e}") from e

# Ejemplo de uso (no se ejecutará directamente aquí):
# if __name__ == '__main__':
#     # Para probar, asegúrate de que la variable de entorno GEMINI_API_KEY está configurada
#     # o pasa la clave directamente: ocr_service = OCRService(api_key="TU_API_KEY_AQUI")
#     ocr_service = OCRService() 
#     try:
#         # Reemplaza "ruta/a/tu/ticket.png" con una ruta real a una imagen
#         with open("ruta/a/tu/ticket.png", "rb") as f:
#             image_bytes = f.read()
#         text = ocr_service.extract_text_from_image(image_bytes, language='spa')
#         print("\n--- Texto extraído por Gemini ---")
#         print(text)
#     except FileNotFoundError:
#         print("Archivo de imagen de ejemplo no encontrado.")
#     except RuntimeError as e:
#         print(f"Error de OCR con Gemini: {e}")
#     except ValueError as e:
#         print(f"Error de configuración o datos: {e}") 