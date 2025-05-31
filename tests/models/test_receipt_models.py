import pytest
from pydantic import ValidationError
from app.models.receipt import ReceiptParseResponse, Item, ItemAssignment, UserShare, ReceiptSplitResponse
from datetime import datetime

def test_item_creation_valid():
    """Prueba la creación de un Item con datos válidos"""
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


def test_receipt_parse_response_creation_valid():
    """Prueba la creación de un ReceiptParseResponse con datos válidos"""
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


def test_item_assignment_creation_valid():
    """Prueba la creación de un ItemAssignment válido"""
    # Arrange & Act
    assignment = ItemAssignment(
        item_id=0,
        quantity=2.5
    )
    
    # Assert
    assert assignment.item_id == 0
    assert assignment.quantity == 2.5

def test_item_assignment_creation_invalid():
    """Prueba la creación de un ItemAssignment inválido"""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        ItemAssignment(
            item_id=0,
            quantity=-1  # Cantidad negativa
        )

def test_user_share_creation_valid():
    """Prueba la creación de un UserShare válido"""
    # Arrange
    items = [Item(id=0, name="Café", quantity=1, price=2.50, total_price=2.50)]
    shared_items = [Item(id=1, name="Tostada", quantity=1, price=3.00, total_price=3.00)]
    
    # Act
    share = UserShare(
        user_id="Juan",
        amount_due=5.50,
        items=items,
        shared_items=shared_items
    )
    
    # Assert
    assert share.user_id == "Juan"
    assert share.amount_due == 5.50
    assert len(share.items) == 1
    assert len(share.shared_items) == 1

def test_receipt_split_response_creation_valid():
    """Prueba la creación de un ReceiptSplitResponse válido"""
    # Arrange
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
        total_calculated=5.50,
        shares=shares
    )
    
    # Assert
    assert response.total_calculated == 5.50
    assert len(response.shares) == 1
    assert response.shares[0].user_id == "Juan" 