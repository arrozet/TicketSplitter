from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from .item import Item
import datetime

class ReceiptBase(BaseModel):
    """
    Modelo base para los datos de un recibo.
    
    Contiene los campos comunes que todo recibo debe tener, independientemente
    de su estado de procesamiento o uso específico.
    
    Attributes:
        filename (Optional[str]): Nombre original del archivo subido.
        upload_timestamp (datetime): Fecha y hora de subida del recibo.
        subtotal (Optional[float]): Subtotal detectado en el recibo.
        tax (Optional[float]): Impuestos detectados en el recibo.
        tip (Optional[float]): Propina detectada en el recibo (si aplica).
        total (Optional[float]): Total general detectado en el recibo.
        raw_text (Optional[str]): Texto crudo extraído del recibo mediante OCR.
    """
    filename: Optional[str] = None # Nombre original del archivo subido.
    upload_timestamp: datetime.datetime # Fecha y hora de subida del recibo.
    subtotal: Optional[float] = None # Subtotal detectado en el recibo.
    tax: Optional[float] = None      # Impuestos detectados en el recibo.
    tip: Optional[float] = None      # Propina detectada en el recibo (si aplica).
    total: Optional[float] = None    # Total general detectado en el recibo.
    raw_text: Optional[str] = None   # Texto crudo extraído del recibo mediante OCR.

class ReceiptCreate(ReceiptBase):
    """
    Modelo para la creación de un recibo.
    
    Hereda de ReceiptBase y está preparado para incluir validaciones adicionales
    específicas para la creación de recibos sin subida de imagen.
    """
    # Modelo para la creación de un recibo (actualmente igual a ReceiptBase).
    # Podría usarse si se crearan recibos directamente sin subida de imagen.
    pass

# Eliminado ReceiptData ya que sus campos están integrados en ReceiptParseResponse
# class ReceiptData(ReceiptBase):
# items: List[Item] = []

# Modelo para la respuesta del endpoint de subida y parseo inicial
class ReceiptParseResponse(ReceiptBase):
    """
    Modelo para la respuesta del endpoint de subida y parseo inicial de recibos.
    
    Extiende ReceiptBase con información específica del procesamiento del recibo,
    incluyendo los items detectados y el estado de validación.
    
    Attributes:
        receipt_id (str): Identificador único asignado al recibo procesado.
        items (List[Item]): Lista de ítems parseados del recibo.
        is_ticket (bool): Indica si la imagen procesada es un ticket válido.
        error_message (Optional[str]): Mensaje de error si la imagen no es un ticket válido.
        detected_content (Optional[str]): Descripción de lo que se detectó en la imagen si no es un ticket.
    """
    receipt_id: str # Identificador único asignado al recibo procesado (ej. UUID).
    items: List[Item] = Field(default_factory=list) # Lista de ítems parseados del recibo.
    is_ticket: bool = Field(default=True, description="Indica si la imagen procesada es un ticket válido")
    error_message: Optional[str] = Field(default=None, description="Mensaje de error si la imagen no es un ticket válido")
    detected_content: Optional[str] = Field(default=None, description="Descripción de lo que se detectó en la imagen si no es un ticket")

class ItemAssignment(BaseModel):
    """
    Modelo para representar la asignación de una cantidad específica de un elemento.
    
    Se utiliza para especificar qué cantidad de un ítem se asigna a un usuario
    en el proceso de división del recibo.
    
    Attributes:
        item_id (int): Identificador del ítem a asignar.
        quantity (float): Cantidad asignada del elemento (debe ser mayor que 0).
    """
    item_id: int
    quantity: float = Field(gt=0, description="Cantidad asignada del elemento (debe ser mayor que 0)")

class ReceiptSplitRequest(BaseModel):
    """
    Modelo para la solicitud de división de un recibo.
    
    Especifica cómo asignar ítems a diferentes usuarios, soportando tanto
    asignaciones simples por ID como asignaciones detalladas por cantidad.
    
    Attributes:
        user_item_assignments (Dict[str, Union[List[int], List[ItemAssignment]]]): 
            Diccionario donde cada clave es un nombre de usuario y el valor es una lista
            de IDs de ítems o asignaciones detalladas asignados a ese usuario.
    
    Examples:
        # Asignación simple por ID:
        {"Alice": [1, 2], "Bob": [3]}
        
        # Asignación detallada por cantidad:
        {"Alice": [{"item_id": 1, "quantity": 2.0}, {"item_id": 2, "quantity": 1.0}],
         "Bob": [{"item_id": 1, "quantity": 1.0}]}
    """
    user_item_assignments: Dict[str, Union[List[int], List[ItemAssignment]]] = Field(
        ..., 
        description="Diccionario donde cada clave es un nombre de usuario (string) y el valor es una lista de IDs de ítems (int) o asignaciones detalladas (ItemAssignment) asignados a ese usuario."
    )
    # Consideraciones futuras:
    # - Manejo de ítems compartidos explícitamente.
    # - Distribución personalizada de impuestos y propinas.

class UserShare(BaseModel):
    """
    Modelo que representa la parte que le corresponde a un usuario en un recibo dividido.
    
    Contiene toda la información necesaria para mostrar a un usuario qué debe pagar
    y qué items se le han asignado.
    
    Attributes:
        user_id (str): Identificador del usuario (ej. nombre proporcionado en la UI).
        amount_due (float): Cantidad total que este usuario debe pagar.
        items (List[Item]): Lista de ítems asignados específicamente a este usuario.
        shared_items (List[Item]): Lista de ítems compartidos con otros usuarios.
    """
    user_id: str # Identificador del usuario (ej. nombre proporcionado en la UI).
    amount_due: float # Cantidad total que este usuario debe pagar.
    items: List[Item] # Lista de ítems (completos) que se le asignaron o contribuyeron a su total.
    shared_items: List[Item] = Field(default_factory=list) # Lista de ítems compartidos (no asignados específicamente).

class ReceiptSplitResponse(BaseModel):
    """
    Modelo para la respuesta de una solicitud de división de recibo.
    
    Contiene el resultado del proceso de división, incluyendo el total calculado
    y las participaciones de cada usuario.
    
    Attributes:
        total_calculated (float): Suma total de las partes calculadas para todos los usuarios.
        shares (List[UserShare]): Lista de las participaciones de cada usuario.
    
    Note:
        El total_calculado puede diferir ligeramente del total original del recibo
        debido a redondeos o a la forma en que se distribuyen costos comunes.
    """
    total_calculated: float # Suma total de las partes calculadas para todos los usuarios.
    shares: List[UserShare] # Lista de las participaciones de cada usuario.

class ReceiptProcessRequest(BaseModel):
    """
    Modelo para opciones de procesamiento de recibos.
    
    Preparado para futuras extensiones que puedan incluir opciones como:
    - Forzar moneda específica
    - Especificar región para mejorar OCR
    - Configuraciones de procesamiento personalizadas
    """
    # Podríamos añadir opciones de procesamiento aquí si fuera necesario
    # por ejemplo, forzar moneda, o región para mejorar OCR.
    pass