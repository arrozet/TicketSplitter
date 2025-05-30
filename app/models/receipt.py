from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from .item import Item
import datetime

class ReceiptBase(BaseModel):
    # Modelo base para los datos de un recibo.
    filename: Optional[str] = None # Nombre original del archivo subido.
    upload_timestamp: datetime.datetime # Fecha y hora de subida del recibo.
    subtotal: Optional[float] = None # Subtotal detectado en el recibo.
    tax: Optional[float] = None      # Impuestos detectados en el recibo.
    tip: Optional[float] = None      # Propina detectada en el recibo (si aplica).
    total: Optional[float] = None    # Total general detectado en el recibo.
    raw_text: Optional[str] = None   # Texto crudo extraído del recibo mediante OCR.

class ReceiptCreate(ReceiptBase):
    # Modelo para la creación de un recibo (actualmente igual a ReceiptBase).
    # Podría usarse si se crearan recibos directamente sin subida de imagen.
    pass

# Eliminado ReceiptData ya que sus campos están integrados en ReceiptParseResponse
# class ReceiptData(ReceiptBase):
# items: List[Item] = []

# Modelo para la respuesta del endpoint de subida y parseo inicial
class ReceiptParseResponse(ReceiptBase):
    # Extiende ReceiptBase con información específica post-procesamiento.
    receipt_id: str # Identificador único asignado al recibo procesado (ej. UUID).
    items: List[Item] = Field(default_factory=list) # Lista de ítems parseados del recibo.
    is_ticket: bool = Field(default=True, description="Indica si la imagen procesada es un ticket válido")
    error_message: Optional[str] = Field(default=None, description="Mensaje de error si la imagen no es un ticket válido")
    detected_content: Optional[str] = Field(default=None, description="Descripción de lo que se detectó en la imagen si no es un ticket")

class ItemAssignment(BaseModel):
    # Modelo para representar la asignación de una cantidad específica de un elemento
    item_id: int
    quantity: float = Field(gt=0, description="Cantidad asignada del elemento (debe ser mayor que 0)")

class ReceiptSplitRequest(BaseModel):
    # Modelo para la solicitud de división de un recibo.
    # Especifica cómo asignar ítems a diferentes usuarios.
    # Ahora soporta asignaciones por cantidad:
    # Ejemplo: {"Alice": [{"item_id": 1, "quantity": 2.0}, {"item_id": 2, "quantity": 1.0}], "Bob": [{"item_id": 1, "quantity": 1.0}]}
    # También mantiene compatibilidad con el formato anterior:
    # Ejemplo: {"Alice": [1, 2], "Bob": [3]} (IDs de ítems del ReceiptParseResponse)
    user_item_assignments: Dict[str, Union[List[int], List[ItemAssignment]]] = Field(
        ..., 
        description="Diccionario donde cada clave es un nombre de usuario (string) y el valor es una lista de IDs de ítems (int) o asignaciones detalladas (ItemAssignment) asignados a ese usuario."
    )
    # Consideraciones futuras:
    # - Manejo de ítems compartidos explícitamente.
    # - Distribución personalizada de impuestos y propinas.

class UserShare(BaseModel):
    # Modelo que representa la parte que le corresponde a un usuario.
    user_id: str # Identificador del usuario (ej. nombre proporcionado en la UI).
    amount_due: float # Cantidad total que este usuario debe pagar.
    items: List[Item] # Lista de ítems (completos) que se le asignaron o contribuyeron a su total.
    shared_items: List[Item] = Field(default_factory=list) # Lista de ítems compartidos (no asignados específicamente).

class ReceiptSplitResponse(BaseModel):
    # Modelo para la respuesta de una solicitud de división.
    total_calculated: float # Suma total de las partes calculadas para todos los usuarios.
                            # Puede diferir ligeramente del 'total' original del recibo debido a redondeos
                            # o a la forma en que se distribuyen costos comunes.
    shares: List[UserShare] # Lista de las participaciones de cada usuario.

class ReceiptProcessRequest(BaseModel):
    # Podríamos añadir opciones de procesamiento aquí si fuera necesario
    # por ejemplo, forzar moneda, o región para mejorar OCR.
    pass