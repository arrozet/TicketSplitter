import pytesseract
from PIL import Image
import io
import cv2
import numpy as np
import os # Importar os para leer variables de entorno

class OCRService:
    def __init__(self, tesseract_cmd: str = None):
        """
        Inicializa el servicio OCR.
        Args:
            tesseract_cmd: Ruta al ejecutable de Tesseract. Si es None, se intenta leer
                           de la variable de entorno TESSERACT_PATH o se asume que está en el PATH del sistema.
                           Ejemplo en Windows: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        """
        cmd_to_use = tesseract_cmd
        if not cmd_to_use:
            cmd_to_use = os.getenv("TESSERACT_PATH")

        if cmd_to_use:
            # Solo asigna pytesseract.tesseract_cmd si se proporciona una ruta explícita
            # o se encuentra en la variable de entorno.
            # Si sigue siendo None, pytesseract buscará en el PATH del sistema.
            pytesseract.tesseract_cmd = cmd_to_use
            print(f"Usando tesseract_cmd: {cmd_to_use}") # Log para depuración
        else:
            print("Tesseract_cmd no especificado ni encontrado en TESSERACT_PATH. Asumiendo que está en el PATH del sistema.")

    def _preprocess_image_for_ocr(self, image_bytes: bytes) -> Image.Image:
        """
        Preprocesa la imagen para mejorar los resultados del OCR.
        Esto puede incluir: conversión a escala de grises, binarización, eliminación de ruido.
        """
        try:
            # Convertir bytes a imagen de OpenCV
            image_np = np.frombuffer(image_bytes, np.uint8)
            img_cv = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

            if img_cv is None:
                # Si OpenCV no puede decodificar, intenta con PIL directamente
                image = Image.open(io.BytesIO(image_bytes))
                return image.convert('L') # Convertir a escala de grises con PIL

            # 1. Convertir a escala de grises
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # 2. Aplicar umbral adaptativo para binarizar la imagen
            #    Esto puede ayudar con diferentes condiciones de iluminación en el ticket.
            # processed_img = cv2.adaptiveThreshold(
            #     gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            #     cv2.THRESH_BINARY, 11, 2
            # )

            # O usar umbral de Otsu si el histograma es bimodal
            _, processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # (Opcional) Dilatación y erosión para eliminar ruido
            # kernel = np.ones((1, 1), np.uint8)
            # processed_img = cv2.dilate(processed_img, kernel, iterations=1)
            # processed_img = cv2.erode(processed_img, kernel, iterations=1)

            # (Opcional) Suavizado para reducir ruido
            # processed_img = cv2.medianBlur(processed_img, 1)
            # processed_img = cv2.GaussianBlur(processed_img, (3,3), 0)

            # Convertir de vuelta a imagen PIL
            pil_image = Image.fromarray(processed_img)
            return pil_image
        except Exception as e:
            print(f"Error en preprocesamiento de imagen: {e}. Usando imagen original.")
            # Fallback a PIL directamente si hay errores con OpenCV
            return Image.open(io.BytesIO(image_bytes)).convert('L')

    def extract_text_from_image(self, image_bytes: bytes, language: str = 'spa') -> str:
        """
        Extrae texto de una imagen usando Tesseract OCR.

        Args:
            image_bytes: La imagen en formato de bytes.
            language: El idioma para OCR (por defecto 'spa' para español).
                      Se pueden usar múltiples idiomas, ej: 'spa+eng'.

        Returns:
            El texto extraído de la imagen.
        """
        try:
            # Preprocesar la imagen
            # image = Image.open(io.BytesIO(image_bytes))
            # preprocessed_image = self._preprocess_image_for_ocr(image)
            preprocessed_image = self._preprocess_image_for_ocr(image_bytes)

            # Configuración para Tesseract
            # PSM 6: Asumir un solo bloque uniforme de texto.
            # PSM 4: Asumir una sola columna de texto de tamaños variables.
            # PSM 11: Texto disperso.
            # PSM 3: Completamente automático (default)
            custom_config = r'--oem 3 --psm 6' # Ajustar PSM según la naturaleza de los tickets

            text = pytesseract.image_to_string(preprocessed_image, lang=language, config=custom_config)
            return text
        except pytesseract.TesseractNotFoundError:
            # Esta excepción es crucial. Informa al usuario que Tesseract no está instalado/configurado.
            error_msg = ("Tesseract no encontrado. Asegúrate de que esté instalado y en tu PATH, "
                         "o especifica la ruta con 'tesseract_cmd' al inicializar OCRService.")
            print(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            print(f"Error durante OCR: {e}")
            # Considerar si relanzar la excepción o devolver un string vacío/None
            raise

# Ejemplo de uso (no se ejecutará directamente aquí):
# if __name__ == '__main__':
#     ocr_service = OCRService() # Añadir ruta si es necesario: OCRService(tesseract_cmd=r'C:\path\to\tesseract.exe')
#     try:
#         with open("path/to/your/receipt.png", "rb") as f:
#             image_bytes = f.read()
#         text = ocr_service.extract_text_from_image(image_bytes, language='spa')
#         print("Texto extraído:")
#         print(text)
#     except FileNotFoundError:
#         print("Archivo de imagen de ejemplo no encontrado.")
#     except RuntimeError as e:
#         print(f"Error de OCR: {e}") 