from pydantic import BaseModel
# Retirado Optional de typing ya que no se usa directamente.

class ItemBase(BaseModel):
    name: str
    quantity: float = 1.0 # Cantidad, puede ser float para items por peso/volumen.
    price: float # Precio unitario del ítem.

class ItemCreate(ItemBase):
    # Modelo para crear un nuevo ítem, actualmente igual a ItemBase.
    # Podría tener validaciones adicionales en el futuro.
    pass

class Item(ItemBase):
    # Modelo completo del ítem, como se devuelve en la API o se usa internamente.
    id: int # Identificador único del ítem dentro de un ticket procesado.
    total_price: float # Precio total para este ítem (quantity * price).

    class Config:
        # Deprecation warning: `orm_mode` es obsoleto, se usa `from_attributes` en Pydantic V2.
        # Permite que el modelo Pydantic se cree a partir de atributos de un objeto (ej. un ORM).
        from_attributes = True 