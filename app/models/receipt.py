from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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

class ReceiptSplitRequest(BaseModel):
    # Modelo para la solicitud de división de un recibo.
    # Especifica cómo asignar ítems a diferentes usuarios.
    # Ejemplo: {"Alice": [1, 2], "Bob": [3]} (IDs de ítems del ReceiptParseResponse)
    user_item_assignments: Dict[str, List[int]] = Field(
        ..., 
        description="Diccionario donde cada clave es un nombre de usuario (string) y el valor es una lista de IDs de ítems (int) asignados a ese usuario."
    )
    # Consideraciones futuras:
    # - Manejo de ítems compartidos explícitamente.
    # - Distribución personalizada de impuestos y propinas.

class UserShare(BaseModel):
    # Modelo que representa la parte que le corresponde a un usuario.
    user_id: str # Identificador del usuario (ej. nombre proporcionado en la UI).
    amount_due: float # Cantidad total que este usuario debe pagar.
    items: List[Item] # Lista de ítems (completos) que se le asignaron o contribuyeron a su total.

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