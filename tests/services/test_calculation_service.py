import pytest
from app.services.calculation_service import CalculationService
from app.models.item import Item
from app.models.receipt import ReceiptParseResponse, ReceiptSplitRequest, ItemAssignment
import datetime
import sys

class TestCalculationService:
    """
    Pruebas unitarias para CalculationService usando patrón AAA.
    Formato de nombres: method_test_result
    """

    @pytest.fixture
    def calculationService(self):
        """Fixture para obtener una instancia del CalculationService"""
        return CalculationService()

    @pytest.fixture
    def sample_receipt_data(self):
        """Fixture para obtener datos de recibo de ejemplo"""
        return ReceiptParseResponse(
            receipt_id="test-123",
            items=[
                Item(id=1, name="Café", quantity=1, price=2.50, total_price=2.50),
                Item(id=2, name="Tostada", quantity=2, price=3.00, total_price=6.00),
                Item(id=3, name="Agua", quantity=1, price=1.50, total_price=1.50)
            ],
            subtotal=10.00,
            tax=1.00,
            total=11.00,
            upload_timestamp=datetime.datetime.now(),
            is_ticket=True
        )

    def test_calculateShares_simpleSplit_returnsCorrectShares(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares con división simple devuelve las partes correctas"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [1, 2],  # Café y Tostada
                "Bob": [3]        # Agua
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        assert resultado.total_calculated == 11.00
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert alice_share.amount_due == 9.35  # 8.50 + 0.85 (IVA proporcional)
        assert len(alice_share.items) == 2
        assert alice_share.items[0].name == "Café"
        assert alice_share.items[1].name == "Tostada"
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert bob_share.amount_due == 1.65  # 1.50 + 0.15 (IVA proporcional)
        assert len(bob_share.items) == 1
        assert bob_share.items[0].name == "Agua"

    def test_calculateShares_partialQuantities_returnsCorrectShares(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares con cantidades parciales devuelve las partes correctas"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [ItemAssignment(item_id=2, quantity=1)],  # 1 Tostada
                "Bob": [ItemAssignment(item_id=2, quantity=1)]     # 1 Tostada
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        assert resultado.total_calculated == 11.00  # Total original del recibo
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert alice_share.amount_due == 5.50  # 3.00 (1 tostada) + 2.50 (compartido)
        assert len(alice_share.items) == 1
        assert alice_share.items[0].name == "Tostada"
        assert alice_share.items[0].quantity == 1
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert bob_share.amount_due == 5.50  # 3.00 (1 tostada) + 2.50 (compartido)
        assert len(bob_share.items) == 1
        assert bob_share.items[0].name == "Tostada"
        assert bob_share.items[0].quantity == 1

    def test_calculateShares_noAssignments_returnsEmptyShares(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares sin asignaciones devuelve partes vacías"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={}
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 0
        assert resultado.total_calculated == 0

    def test_calculateShares_unassignedItems_areShared(self, calculationService, sample_receipt_data):
        """Prueba que los items no asignados se comparten entre todos los usuarios"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [1],  # Solo Café
                "Bob": []      # Sin asignaciones específicas
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert len(alice_share.shared_items) == 2  # Tostada y Agua compartidos
        assert any(item.name == "Tostada" for item in alice_share.shared_items)
        assert any(item.name == "Agua" for item in alice_share.shared_items)
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert len(bob_share.shared_items) == 2  # Tostada y Agua compartidos
        assert any(item.name == "Tostada" for item in bob_share.shared_items)
        assert any(item.name == "Agua" for item in bob_share.shared_items)

    def test_calculateShares_exceedsQuantity_adjustsToAvailable(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares ajusta las cantidades si exceden lo disponible"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [ItemAssignment(item_id=2, quantity=3)],  # Intenta asignar 3 tostadas cuando solo hay 2
                "Bob": [ItemAssignment(item_id=2, quantity=1)]     # 1 tostada
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert alice_share.items[0].quantity == 2  # Se ajusta a 2 tostadas (la cantidad disponible)
        assert alice_share.items[0].total_price == 6.00  # Precio de 2 tostadas
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert len(bob_share.items) == 0  # No recibe tostadas porque Alice ya tomó todas las disponibles

    def test_calculateShares_invalidItemId_ignoresAssignment(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares ignora asignaciones con IDs de items inválidos"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [999],  # ID de item inexistente
                "Bob": [1]       # Item válido
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert len(alice_share.items) == 0  # No tiene items asignados
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert len(bob_share.items) == 1  # Tiene el Café asignado
        assert bob_share.items[0].name == "Café"

    def test_calculateShares_duplicateAssignment_handlesCorrectly(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares maneja correctamente asignaciones duplicadas del mismo item"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [1, 1],  # Intenta asignar el Café dos veces
                "Bob": [1]        # También intenta asignar el Café
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert len(alice_share.items) == 1  # Solo tiene el Café una vez
        assert alice_share.items[0].name == "Café"
        assert alice_share.items[0].quantity == 1  # Cantidad correcta
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert len(bob_share.items) == 0  # No tiene items asignados porque Alice ya tomó el Café 

    def test_calculateShares_noQuantityAvailable_ignoresAssignment(self, calculationService, sample_receipt_data):
        """Prueba que calculateShares ignora asignaciones cuando no hay cantidad disponible"""
        # Arrange
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [ItemAssignment(item_id=2, quantity=2)],  # Toma todas las tostadas
                "Bob": [ItemAssignment(item_id=2, quantity=1)]     # Intenta tomar una tostada cuando ya no hay
            }
        )

        # Act
        resultado = calculationService.calculateShares(sample_receipt_data, split_request)

        # Assert
        assert len(resultado.shares) == 2
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert len(alice_share.items) == 1
        assert alice_share.items[0].name == "Tostada"
        assert alice_share.items[0].quantity == 2  # Tiene todas las tostadas
        assert alice_share.items[0].total_price == 6.00  # Precio de 2 tostadas
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert len(bob_share.items) == 0  # No recibe tostadas porque ya no hay disponibles 

    def test_calculateShares_noUsersNoItems_returnsEmptyResponse(self, calculationService):
        """Prueba que calculateShares devuelve respuesta vacía cuando no hay usuarios ni items"""
        # Arrange
        empty_receipt = ReceiptParseResponse(
            receipt_id="test-empty",
            items=[],
            subtotal=0,
            tax=0,
            total=0,
            upload_timestamp=datetime.datetime.now(),
            is_ticket=True
        )
        split_request = ReceiptSplitRequest(user_item_assignments={})

        # Act
        resultado = calculationService.calculateShares(empty_receipt, split_request)

        # Assert
        assert resultado.total_calculated == 0
        assert len(resultado.shares) == 0

    def test_calculateShares_noUsersWithItems_returnsEmptyResponse(self, calculationService):
        """Prueba que calculateShares devuelve respuesta vacía cuando hay items pero no usuarios"""
        # Arrange
        receipt_with_items = ReceiptParseResponse(
            receipt_id="test-items",
            items=[
                Item(id=1, name="Café", quantity=1, price=2.50, total_price=2.50)
            ],
            subtotal=2.50,
            tax=0.25,
            total=2.75,
            upload_timestamp=datetime.datetime.now(),
            is_ticket=True
        )
        split_request = ReceiptSplitRequest(user_item_assignments={})

        # Act
        resultado = calculationService.calculateShares(receipt_with_items, split_request)

        # Assert
        assert resultado.total_calculated == 0
        assert len(resultado.shares) == 0

    def test_calculateShares_includedVAT_handlesCorrectly(self, calculationService):
        """Prueba que calculateShares maneja correctamente cuando el IVA está incluido en los precios"""
        # Arrange
        receipt_with_included_vat = ReceiptParseResponse(
            receipt_id="test-vat",
            items=[
                Item(id=1, name="Café", quantity=1, price=2.50, total_price=2.50),
                Item(id=2, name="Tostada", quantity=1, price=3.00, total_price=3.00)
            ],
            subtotal=5.50,  # IVA incluido
            tax=0,          # No hay IVA adicional
            total=5.50,     # Total igual al subtotal
            upload_timestamp=datetime.datetime.now(),
            is_ticket=True
        )
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [1],  # Café
                "Bob": [2]     # Tostada
            }
        )

        # Act
        resultado = calculationService.calculateShares(receipt_with_included_vat, split_request)

        # Assert
        assert resultado.total_calculated == 5.50
        
        # Verificar parte de Alice
        alice_share = next(share for share in resultado.shares if share.user_id == "Alice")
        assert alice_share.amount_due == 2.50  # Solo el precio del café, sin IVA adicional
        
        # Verificar parte de Bob
        bob_share = next(share for share in resultado.shares if share.user_id == "Bob")
        assert bob_share.amount_due == 3.00  # Solo el precio de la tostada, sin IVA adicional 

    def test_calculateShares_prints_warning_when_item_fully_assigned(self, calculationService, sample_receipt_data, capsys):
        """Prueba que se imprime advertencia cuando un item ya está completamente asignado"""
        # Arrange: Alice toma todas las tostadas, Bob intenta tomar una más
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [ItemAssignment(item_id=2, quantity=2)],
                "Bob": [ItemAssignment(item_id=2, quantity=1)]
            }
        )
        # Act
        calculationService.calculateShares(sample_receipt_data, split_request)
        captured = capsys.readouterr()
        # Assert
        assert "ya está completamente asignado" in captured.out

    def test_calculateShares_prints_warning_when_item_id_not_found(self, calculationService, sample_receipt_data, capsys):
        """Prueba que se imprime advertencia cuando se asigna un item inexistente"""
        # Arrange: Alice intenta asignar un item que no existe usando ItemAssignment
        split_request = ReceiptSplitRequest(
            user_item_assignments={
                "Alice": [ItemAssignment(item_id=999, quantity=1)]
            }
        )
        # Act
        calculationService.calculateShares(sample_receipt_data, split_request)
        captured = capsys.readouterr()
        # Assert
        assert "no encontrado en el ticket" in captured.out 