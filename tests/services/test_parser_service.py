import pytest
import json
from unittest.mock import patch, Mock
from app.services.parser_service import ParserService
from app.models.item import Item


class TestParserService:
    """
    Pruebas unitarias para ParserService usando patrón AAA.
    Formato de nombres: method_test_result
    """

    # Un fixture es una función que proporciona datos o configuración reutilizable para las pruebas
    # En este caso, crea una nueva instancia de ParserService para cada prueba
    @pytest.fixture
    def parserService(self):
        """Fixture para obtener una instancia del ParserService"""
        return ParserService()

    # ============== TESTS FOR parseTextToItems ==============

    def test_parseTextToItems_validJson_returnsCorrectData(self, parserService):
        """Prueba que parseTextToItems con JSON válido devuelve los datos correctos"""
        # Arrange
        json_valido = json.dumps({
            "items": [
                {"description": "Café", "quantity": 1, "unit_price": 2.50},
                {"description": "Tostada", "quantity": 2, "unit_price": 3.00}
            ],
            "subtotal": 8.50,
            "tax": 0.85,
            "total": 9.35
        })

        # Act
        resultado = parserService.parseTextToItems(json_valido)

        # Assert
        assert len(resultado["items"]) == 2
        assert resultado["items"][0].name == "Café"
        assert resultado["items"][0].quantity == 1
        assert resultado["items"][0].price == 2.50
        assert resultado["items"][0].total_price == 2.50
        assert resultado["items"][1].name == "Tostada"
        assert resultado["items"][1].quantity == 2
        assert resultado["items"][1].price == 3.00
        assert resultado["items"][1].total_price == 6.00
        assert resultado["subtotal"] == 8.50
        assert resultado["tax"] == 0.85
        assert resultado["total"] == 9.35
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_malformedJson_returnsEmptyData(self, parserService):
        """Prueba que parseTextToItems con JSON malformado devuelve datos vacíos"""
        # Arrange
        json_malformado = '{"items": [{"description": "Café", "quantity": 1'  # JSON incompleto

        # Act
        resultado = parserService.parseTextToItems(json_malformado)

        # Assert
        assert len(resultado["items"]) == 0
        assert resultado["subtotal"] is None
        assert resultado["tax"] is None
        assert resultado["total"] is None
        assert resultado["raw_text"] == json_malformado
        assert resultado["is_ticket"] is True  # El servicio marca como ticket válido incluso con JSON malformado


    def test_parseTextToItems_noTotals_calculatesTotalAutomatically(self, parserService):
        """Prueba que parseTextToItems sin totales calcula el total automáticamente"""
        # Arrange
        json_sin_totales = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 2, "unit_price": 5.00},
                {"description": "Item 2", "quantity": 1, "unit_price": 10.00}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(json_sin_totales)

        # Assert
        assert len(resultado["items"]) == 2
        assert resultado["total"] == 20.00  # (2 * 5.00) + (1 * 10.00)
        assert resultado["subtotal"] == 20.00
        assert resultado["tax"] is None  # El servicio no establece tax a 0 por defecto
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_withSubtotalAndTax_calculatesTotal(self, parserService):
        """Prueba que parseTextToItems con subtotal y tax calcula el total"""
        # Arrange
        json_con_subtotal_tax = json.dumps({
            "items": [
                {"description": "Item", "quantity": 1, "unit_price": 10.00}
            ],
            "subtotal": 10.00,
            "tax": 1.00
            # Sin total
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_subtotal_tax)

        # Assert
        assert resultado["total"] == 10.00  # Total calculado de items (1 * 10.00)
        assert resultado["subtotal"] == 10.00
        assert resultado["tax"] == 1.00
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_withTotalAndTax_calculatesSubtotal(self, parserService):
        """Prueba que parseTextToItems con total y tax calcula el subtotal"""
        # Arrange
        json_con_total_tax = json.dumps({
            "items": [
                {"description": "Item", "quantity": 1, "unit_price": 10.00}
            ],
            "tax": 1.00,
            "total": 11.00
            # Sin subtotal
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_total_tax)

        # Assert
        assert resultado["subtotal"] == 10.00
        assert resultado["tax"] == 1.00
        assert resultado["total"] == 11.00
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_itemsWithoutDescription_areIgnored(self, parserService):
        """Prueba que parseTextToItems ignora items sin descripción"""
        # Arrange
        json_con_item_sin_descripcion = json.dumps({
            "items": [
                {"quantity": 1, "unit_price": 10.00},  # Sin description
                {"description": "Item válido", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_item_sin_descripcion)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].name == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_itemsWithoutPrice_areIgnored(self, parserService):
        """Prueba que parseTextToItems ignora items sin precio unitario"""
        # Arrange
        json_con_item_sin_precio = json.dumps({
            "items": [
                {"description": "Item sin precio", "quantity": 1},  # Sin unit_price
                {"description": "Item válido", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_item_sin_precio)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].name == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_zeroPrice_isValid(self, parserService):
        """Prueba que parseTextToItems acepta items con precio cero"""
        # Arrange
        json_con_precio_cero = json.dumps({
            "items": [
                {"description": "Item gratis", "quantity": 1, "unit_price": 0.0},
                {"description": "Item normal", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_precio_cero)

        # Assert
        assert len(resultado["items"]) == 2
        assert resultado["items"][0].price == 0.0
        assert resultado["items"][0].total_price == 0.0
        assert resultado["items"][1].price == 5.00
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_emptyJson_returnsEmptyStructure(self, parserService):
        """Prueba que parseTextToItems con JSON vacío devuelve estructura vacía esperada"""
        # Arrange
        json_vacio = json.dumps({})

        # Act
        resultado = parserService.parseTextToItems(json_vacio)

        # Assert
        assert len(resultado["items"]) == 0
        assert resultado["subtotal"] is None
        assert resultado["tax"] is None
        assert resultado["total"] is None
        assert resultado["is_ticket"] is True  # El servicio marca como ticket válido incluso con JSON vacío
        if resultado["error_message"] is not None:
            assert "No se encontraron items" in resultado["error_message"]

    def test_parseTextToItems_nullValues_handledCorrectly(self, parserService):
        """Prueba que parseTextToItems maneja valores null en JSON para precios y cantidades"""
        # Arrange
        json_con_nulls = json.dumps({
            "items": [
                {"description": "Item con precio null", "quantity": 1, "unit_price": None},
                {"description": "Item con cantidad null", "quantity": None, "unit_price": 10.00},
                {"description": "Item válido", "quantity": 1, "unit_price": 5.00}
            ],
            "subtotal": None,
            "tax": None,
            "total": None
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_nulls)

        # Assert
        assert len(resultado["items"]) == 2  # El servicio acepta items con cantidad null pero no con precio null
        assert resultado["items"][0].name == "Item con cantidad null"
        assert resultado["items"][1].name == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def test_parseTextToItems_multipleIds_assignsSequentialIds(self, parserService):
        """Prueba que parseTextToItems asigna IDs secuenciales a los items"""
        # Arrange
        json_con_multiples_items = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 1, "unit_price": 1.00},
                {"description": "Item 2", "quantity": 1, "unit_price": 2.00},
                {"description": "Item 3", "quantity": 1, "unit_price": 3.00}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_multiples_items)

        # Assert
        assert resultado["items"][0].id == 1
        assert resultado["items"][1].id == 2
        assert resultado["items"][2].id == 3

    def test_parseTextToItems_multipleCalls_resetsIds(self, parserService):
        """Prueba que los IDs de los items se reinician en múltiples llamadas a parseTextToItems"""
        # Arrange
        json_items_1 = json.dumps({"items": [{"description": "A", "quantity": 1, "unit_price": 1}]})
        json_items_2 = json.dumps({"items": [{"description": "B", "quantity": 1, "unit_price": 1}]})

        # Act
        resultado1 = parserService.parseTextToItems(json_items_1)
        resultado2 = parserService.parseTextToItems(json_items_2)

        # Assert
        assert resultado1["items"][0].id == 1
        assert resultado2["items"][0].id == 1 # ID debe ser 1 de nuevo

    def test_parseTextToItems_notTicket_returnsError(self, parserService):
        """Prueba que parseTextToItems devuelve error cuando no es un ticket"""
        # Arrange
        json_no_ticket = json.dumps({
            "is_ticket": False,
            "error_message": "No es un ticket",
            "detected_content": "Contenido no relacionado"
        })

        # Act
        resultado = parserService.parseTextToItems(json_no_ticket)

        # Assert
        assert resultado["is_ticket"] is False
        assert resultado["error_message"] == "No es un ticket"
        assert resultado["detected_content"] == "Contenido no relacionado"
        assert len(resultado["items"]) == 0

    def test_parsePrice_invalidType_returnsNone(self, parserService):
        """Prueba que _parsePrice devuelve None para tipos inválidos"""
        # Arrange
        precio_invalido = {"tipo": "invalido"}

        # Act
        resultado = parserService._parsePrice(precio_invalido)

        # Assert
        assert resultado is None

    def test_parseQuantity_invalidType_returnsOne(self, parserService):
        """Prueba que _parseQuantity devuelve 1.0 para tipos inválidos"""
        # Arrange
        cantidad_invalida = {"tipo": "invalido"}

        # Act
        resultado = parserService._parseQuantity(cantidad_invalida)

        # Assert
        assert resultado == 1.0

    def test_parseTextToItems_calculatesSubtotalFromTotalAndTax(self, parserService):
        """Prueba que parseTextToItems calcula el subtotal cuando solo hay total e impuestos"""
        # Arrange
        json_con_total_tax = json.dumps({
            "items": [
                {"description": "Item", "quantity": 1, "unit_price": 10.00}
            ],
            "total": 11.00,
            "tax": 1.00
            # Sin subtotal
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_total_tax)

        # Assert
        assert resultado["subtotal"] == 10.00  # 11.00 - 1.00
        assert resultado["tax"] == 1.00
        assert resultado["total"] == 11.00

    def test_parseTextToItems_calculatesSubtotalFromTotalAndItems(self, parserService):
        """Prueba que parseTextToItems calcula el subtotal cuando solo hay total e items"""
        # Arrange
        json_con_total_items = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 2, "unit_price": 5.00},
                {"description": "Item 2", "quantity": 1, "unit_price": 10.00}
            ],
            "total": 20.00
            # Sin subtotal ni tax
        })

        # Act
        resultado = parserService.parseTextToItems(json_con_total_items)

        # Assert
        assert resultado["subtotal"] == 20.00  # Suma de items: (2 * 5.00) + (1 * 10.00)
        assert resultado["total"] == 20.00
        assert resultado["tax"] is None

    def test_parsePrice_stringWithComma_returnsFloat(self, parserService):
        """Prueba que _parsePrice maneja correctamente strings con coma"""
        # Arrange
        precio_con_coma = "10,50"

        # Act
        resultado = parserService._parsePrice(precio_con_coma)

        # Assert
        assert resultado == 10.50

    def test_parseQuantity_stringWithComma_returnsFloat(self, parserService):
        """Prueba que _parseQuantity maneja correctamente strings con coma"""
        # Arrange
        cantidad_con_coma = "2,5"

        # Act
        resultado = parserService._parseQuantity(cantidad_con_coma)

        # Assert
        assert resultado == 2.5

    def test_parseTextToItems_noItemsNoTotal_returnsEmptyStructure(self, parserService):
        """Prueba que parseTextToItems maneja correctamente el caso de no items ni total"""
        # Arrange
        json_sin_items_ni_total = json.dumps({
            "items": [],
            "subtotal": None,
            "tax": None,
            "total": None
        })

        # Act
        resultado = parserService.parseTextToItems(json_sin_items_ni_total)

        # Assert
        assert len(resultado["items"]) == 0
        assert resultado["subtotal"] is None
        assert resultado["tax"] is None
        assert resultado["total"] is None
        assert resultado["is_ticket"] is True

    def test_parsePrice_stringInvalid_returnsNone(self, parserService):
        """Prueba que _parsePrice devuelve None si el string no es convertible a float"""
        # Arrange
        precio_invalido = "abc"

        # Act
        resultado = parserService._parsePrice(precio_invalido)

        # Assert
        assert resultado is None

    def test_parseQuantity_stringInvalid_returnsOne(self, parserService):
        """Prueba que _parseQuantity devuelve 1.0 si el string no es convertible a float"""
        # Arrange
        cantidad_invalida = "abc"

        # Act
        resultado = parserService._parseQuantity(cantidad_invalida)

        # Assert
        assert resultado == 1.0

    def test_parseTextToItems_noItemsNoTotal_printsMessage(self, parserService, capsys):
        """Prueba que parseTextToItems ejecuta el print cuando no hay items ni total"""
        # Arrange
        json_sin_items_ni_total = json.dumps({})

        # Act
        parserService.parseTextToItems(json_sin_items_ni_total)
        captured = capsys.readouterr()

        # Assert
        assert "No se encontraron ítems ni total en el JSON de Gemini." in captured.out

    def test_parsePrice_unexpectedType_returnsNone(self, parserService):
        """Prueba que _parsePrice devuelve None para un tipo inesperado (no lanza excepción)"""
        # Arrange
        valor_raro = []
        # Act
        resultado = parserService._parsePrice(valor_raro)
        # Assert
        assert resultado is None

 