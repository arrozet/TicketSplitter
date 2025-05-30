from fastapi import APIRouter, File, UploadFile, HTTPException, Body, Depends
from typing import Dict, Any, List
import datetime
import uuid
import os

from app.services.ocr_service import OCRService
from app.services.parser_service import ParserService
from app.services.calculation_service import CalculationService
from app.models.receipt import ReceiptParseResponse, ReceiptSplitRequest, ReceiptSplitResponse
from app.models.item import Item

router = APIRouter()

# "Base de datos" en memoria para almacenar temporalmente los datos de los tickets procesados.
# La clave es un receipt_id (string UUID), el valor es un objeto ReceiptParseResponse.
# En una aplicación de producción, esto se reemplazaría por una base de datos real (ej. PostgreSQL, MongoDB).
processed_receipts_db: Dict[str, ReceiptParseResponse] = {}

# --- Dependencias de Servicios ---
# Usar Depends de FastAPI permite la inyección de dependencias, facilitando las pruebas
# y la configuración de los servicios (ej. pasar configuraciones específicas).

def getOcrService():
    """Provee una instancia del servicio OCR (ahora usando Gemini)."""
    # OCRService ahora maneja la obtención de la API key desde variables de entorno
    # o usa la que se le pase directamente (o la hardcodeada como fallback).
    # No es necesario pasarle la API key aquí explícitamente si está como variable de entorno GEMINI_API_KEY.
    return OCRService()

def getParserService():
    """Provee una instancia del servicio de parsing."""
    return ParserService()

def getCalculationService():
    """Provee una instancia del servicio de cálculo."""
    return CalculationService()

# --- Endpoints de la API ---

@router.post("/upload", response_model=ReceiptParseResponse)
async def uploadReceiptImage(
    file: UploadFile = File(..., description="Archivo de imagen del ticket (PNG, JPG, etc.)"),
    ocr_service: OCRService = Depends(getOcrService),
    parser_service: ParserService = Depends(getParserService)
):
    """
    Endpoint para subir una imagen de un ticket.
    La imagen se procesa con OCR para extraer texto, y luego se parsea para identificar ítems y totales.
    Devuelve los datos parseados del ticket, incluyendo un ID único para futuras operaciones.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo subido debe ser una imagen.")

    try:
        image_bytes = await file.read()
        # Extraer texto de la imagen usando el servicio OCR
        raw_text = ocr_service.extractTextFromImage(image_bytes)
        # Parsear el texto extraído para obtener items y otros datos
        parsed_data_dict = parser_service.parseTextToItems(raw_text)

        receipt_id = str(uuid.uuid4()) # Generar un ID único para este ticket procesado
        
        # Verificar si la imagen es un ticket válido
        is_ticket = parsed_data_dict.get("is_ticket", True)
        error_message = parsed_data_dict.get("error_message")
        detected_content = parsed_data_dict.get("detected_content")
        
        # Crear el objeto de respuesta con los datos parseados
        response = ReceiptParseResponse(
            receipt_id=receipt_id,
            filename=file.filename,
            upload_timestamp=datetime.datetime.now(datetime.timezone.utc), # Usar UTC para consistencia
            items=parsed_data_dict.get("items", []),
            subtotal=parsed_data_dict.get("subtotal"),
            tax=parsed_data_dict.get("tax"),
            total=parsed_data_dict.get("total"),
            raw_text=raw_text,
            is_ticket=is_ticket,
            error_message=error_message,
            detected_content=detected_content
        )
        
        processed_receipts_db[receipt_id] = response # Guardar en la "DB" en memoria
        
        # Si no es un ticket válido, devolver error 400 con el mensaje DESPUÉS de guardar la respuesta
        if not is_ticket:
            raise HTTPException(
                status_code=400, 
                detail=error_message or "La imagen proporcionada no parece ser un ticket de compra o factura válido."
            )
        
        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar (errores 400, 404, etc.)
        raise
    except RuntimeError as e:
        # Captura específicamente el error si Tesseract no está configurado/instalado
        if "Tesseract no encontrado" in str(e):
            # Es importante dar un error claro al cliente/frontend en este caso.
            raise HTTPException(status_code=500, detail=f"Error de configuración del servidor: {e}")
        # Otros errores de runtime durante el OCR/parsing
        raise HTTPException(status_code=500, detail=f"Error procesando la imagen: {e}")
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        # En producción, se debería loggear este error detalladamente.
        raise HTTPException(status_code=500, detail=f"Error inesperado en el servidor: {e}")

@router.get("/{receipt_id}", response_model=ReceiptParseResponse)
async def getReceiptData(receipt_id: str):
    """
    Obtiene los datos de un ticket procesado previamente, usando su ID.
    """
    receipt_data = processed_receipts_db.get(receipt_id)
    if not receipt_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado con el ID proporcionado.")
    return receipt_data

@router.post("/{receipt_id}/split", response_model=ReceiptSplitResponse)
async def splitReceipt(
    receipt_id: str,
    split_request: ReceiptSplitRequest, # Los datos para la división vienen en el cuerpo del request
    calculation_service: CalculationService = Depends(getCalculationService)
):
    """
    Calcula la división de un ticket (previamente procesado y identificado por `receipt_id`)
    basado en las asignaciones de ítems a usuarios proporcionadas en `split_request`.
    """
    parsed_receipt_data = processed_receipts_db.get(receipt_id)
    if not parsed_receipt_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado para dividir. Primero debe ser subido y procesado.")

    if not parsed_receipt_data.items:
        # No tiene sentido dividir un ticket sin items
        raise HTTPException(status_code=400, detail="El ticket no contiene ítems parseados para dividir.")

    if not split_request.user_item_assignments:
        # Se necesita saber cómo asignar los items
        raise HTTPException(status_code=400, detail="No se proporcionaron asignaciones de usuarios para dividir el ticket.")

    # Validar que todos los IDs de ítems asignados existen en el ticket
    all_item_ids = {item.id for item in parsed_receipt_data.items}
    for user, assignments in split_request.user_item_assignments.items():
        for assignment in assignments:
            if isinstance(assignment, dict):
                item_id = assignment.get('item_id')
            else:
                item_id = assignment if isinstance(assignment, int) else getattr(assignment, 'item_id', None)
            if item_id not in all_item_ids:
                raise HTTPException(status_code=400, detail="Item no encontrado")

    try:
        # Usar el servicio de cálculo para obtener las participaciones
        split_response = calculation_service.calculateShares(parsed_receipt_data, split_request)
        return split_response
    except Exception as e:
        # Capturar errores durante el cálculo de la división
        # En producción, loggear este error.
        raise HTTPException(status_code=500, detail=f"Error calculando la división: {e}")

# Futura consideración: Endpoint para permitir al usuario corregir/actualizar los ítems parseados
# @router.put("/{receipt_id}/items", response_model=ReceiptParseResponse)
# async def updateReceiptItems(receipt_id: str, items_update: List[Item]):
#     if receipt_id not in processed_receipts_db:
#         raise HTTPException(status_code=404, detail="Ticket no encontrado")
#     
#     # Lógica para actualizar los items... puede ser complejo validar
#     # Se necesitaría recalcular totales, etc.
#     # Por ahora, se deja como una idea para mejora.
#     processed_receipts_db[receipt_id].items = items_update
#     # ... (recalcular total, subtotal si es necesario o marcarlos como modificados)
#     return processed_receipts_db[receipt_id] 