from pydantic import BaseModel, ConfigDict
# Retirado Optional de typing ya que no se usa directamente.

class ItemBase(BaseModel):
    """
    Modelo base para representar un ítem en un recibo.
    
    Attributes:
        name (str): Nombre o descripción del ítem.
        quantity (float): Cantidad del ítem. Por defecto es 1.0.
        price (float): Precio unitario del ítem.
    """
    name: str
    quantity: float = 1.0 # Cantidad, puede ser float para items por peso/volumen.
    price: float # Precio unitario del ítem.

class ItemCreate(ItemBase):
    """
    Modelo para la creación de nuevos ítems.
    
    Hereda de ItemBase y está preparado para incluir validaciones adicionales
    específicas para la creación de ítems en el futuro.
    """
    # Modelo para crear un nuevo ítem, actualmente igual a ItemBase.
    # Podría tener validaciones adicionales en el futuro.
    pass

class Item(ItemBase):
    """
    Modelo completo de un ítem tal como se usa en la aplicación.
    
    Este modelo extiende ItemBase añadiendo campos adicionales necesarios
    para el procesamiento completo de ítems en recibos.
    
    Attributes:
        id (int): Identificador único del ítem dentro de un ticket procesado.
        total_price (float): Precio total calculado para este ítem (quantity * price).
    
    Config:
        from_attributes (bool): Permite la creación del modelo a partir de atributos
                              de objetos (útil para ORMs y conversiones).
    """
    # Modelo completo del ítem, como se devuelve en la API o se usa internamente.
    id: int # Identificador único del ítem dentro de un ticket procesado.
    total_price: float # Precio total para este ítem (quantity * price).

    # Configuración actualizada a Pydantic V2
    model_config = ConfigDict(from_attributes=True) 