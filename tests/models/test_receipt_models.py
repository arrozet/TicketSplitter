import pytest
from pydantic import ValidationError
from app.models.receipt import ReceiptParseResponse, Item, ItemAssignment, UserShare, ReceiptSplitResponse
from datetime import datetime

"""
Módulo de pruebas para los modelos de recibo.
Prueba la creación y validación de modelos Pydantic utilizados en la aplicación.
"""

def test_Item_validData_createsItem():
    """
    Prueba la creación exitosa de un Item con datos válidos.
    Verifica que todos los campos se asignen correctamente.
    """
    # Arrange
    item_data = {
        "id": 1,
        "name": "Café",
        "quantity": 1,
        "price": 2.50,
        "total_price": 2.50
    }
    
    # Act
    item = Item(**item_data)
    
    # Assert
    assert item.id == 1
    assert item.name == "Café"
    assert item.quantity == 1
    assert item.price == 2.50
    assert item.total_price == 2.50


def test_ReceiptParseResponse_validData_createsResponse():
    """
    Prueba la creación exitosa de un ReceiptParseResponse con datos válidos.
    Verifica que el modelo se cree con todos los campos correctos incluyendo valores por defecto.
    """
    # Arrange
    items = [
        Item(id=0, name="Café", quantity=1, price=2.50, total_price=2.50),
        Item(id=1, name="Tostada", quantity=2, price=3.00, total_price=6.00)
    ]
    timestamp = datetime.now().isoformat()
    
    # Act
    receipt = ReceiptParseResponse(
        receipt_id="test-123",
        items=items,
        subtotal=8.50,
        tax=0.85,
        total=9.35,
        upload_timestamp=timestamp,
        is_ticket=True
    )
    
    # Assert
    assert receipt.receipt_id == "test-123"
    assert len(receipt.items) == 2
    assert receipt.subtotal == 8.50
    assert receipt.tax == 0.85
    assert receipt.total == 9.35
    assert receipt.is_ticket is True
    assert receipt.error_message is None


def test_ItemAssignment_validData_createsAssignment():
    """
    Prueba la creación exitosa de un ItemAssignment con datos válidos.
    Verifica que se puede asignar una cantidad específica a un item.
    """
    # Arrange
    item_id = 0
    quantity = 2.5
    
    # Act
    assignment = ItemAssignment(
        item_id=item_id,
        quantity=quantity
    )
    
    # Assert
    assert assignment.item_id == 0
    assert assignment.quantity == 2.5

def test_ItemAssignment_negativeQuantity_raisesValidationError():
    """
    Prueba que ItemAssignment rechaza cantidades negativas.
    Verifica que Pydantic valida correctamente el campo quantity.
    """
    # Arrange
    item_id = 0
    negative_quantity = -1
    
    # Act & Assert
    with pytest.raises(ValidationError):
        ItemAssignment(
            item_id=item_id,
            quantity=negative_quantity
        )

def test_UserShare_validData_createsShare():
    """
    Prueba la creación exitosa de un UserShare con datos válidos.
    Verifica que se puede crear una participación de usuario con items asignados y compartidos.
    """
    # Arrange
    user_id = "Juan"
    amount_due = 5.50
    items = [Item(id=0, name="Café", quantity=1, price=2.50, total_price=2.50)]
    shared_items = [Item(id=1, name="Tostada", quantity=1, price=3.00, total_price=3.00)]
    
    # Act
    share = UserShare(
        user_id=user_id,
        amount_due=amount_due,
        items=items,
        shared_items=shared_items
    )
    
    # Assert
    assert share.user_id == "Juan"
    assert share.amount_due == 5.50
    assert len(share.items) == 1
    assert len(share.shared_items) == 1

def test_ReceiptSplitResponse_validData_createsResponse():
    """
    Prueba la creación exitosa de un ReceiptSplitResponse con datos válidos.
    Verifica que se puede crear una respuesta de división con múltiples participaciones.
    """
    # Arrange
    total_calculated = 5.50
    items = [Item(id=0, name="Café", quantity=1, price=2.50, total_price=2.50)]
    shared_items = [Item(id=1, name="Tostada", quantity=1, price=3.00, total_price=3.00)]
    
    shares = [
        UserShare(
            user_id="Juan",
            amount_due=5.50,
            items=items,
            shared_items=shared_items
        )
    ]
    
    # Act
    response = ReceiptSplitResponse(
        total_calculated=total_calculated,
        shares=shares
    )
    
    # Assert
    assert response.total_calculated == 5.50
    assert len(response.shares) == 1
    assert response.shares[0].user_id == "Juan" 