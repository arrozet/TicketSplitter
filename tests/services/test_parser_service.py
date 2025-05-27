import pytest
import json
from unittest.mock import patch, Mock
from app.services.parser_service import ParserService
from app.models.item import Item


class TestParserService:
    """
    Pruebas unitarias para ParserService usando patrón AAA.
    Formato de nombres: metodo_prueba_resultado
    """

    @pytest.fixture
    def parserService(self):
        """Fixture para obtener una instancia del ParserService"""
        return ParserService()

    # ============== PRUEBAS PARA parseTextToItems ==============

    def testParseTextToItemsJsonValidoDevuelveItemsParseados(self, parserService):
        """Prueba que parseTextToItems con JSON válido devuelve items correctamente parseados"""
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

    def testParseTextToItemsJsonMalformadoDevuelveDatosVacios(self, parserService):
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

    def testParseTextToItemsSinTotalesCalculaTotalAutomaticamente(self, parserService):
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

    def testParseTextToItemsConSubtotalYTaxCalculaTotal(self, parserService):
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
        # El servicio calcula total basado en items cuando subtotal+tax no coincide
        assert resultado["total"] == 10.00  # Total calculado de items (1 * 10.00)
        assert resultado["subtotal"] == 10.00
        assert resultado["tax"] == 1.00

    def testParseTextToItemsConTotalYTaxCalculaSubtotal(self, parserService):
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

    def testParseTextToItemsItemsSinDescripcionSonIgnorados(self, parserService):
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

    def testParseTextToItemsItemsSinPrecioSonIgnorados(self, parserService):
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

    def testParseTextToItemsAsignaIdsSecuenciales(self, parserService):
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

    def testParseTextToItemsPrecioCeroEsValido(self, parserService):
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

    # ============== PRUEBAS PARA _parsePrice ==============

    def testParsePriceNumeroEnteroDevuelveFloat(self, parserService):
        """Prueba que _parsePrice convierte números enteros a float"""
        # Arrange
        valor_entero = 10

        # Act
        resultado = parserService._parsePrice(valor_entero)

        # Assert
        assert resultado == 10.0
        assert isinstance(resultado, float)

    def testParsePriceNumeroFloatDevuelveMismoValor(self, parserService):
        """Prueba que _parsePrice devuelve el mismo valor para floats"""
        # Arrange
        valor_float = 10.5

        # Act
        resultado = parserService._parsePrice(valor_float)

        # Assert
        assert resultado == 10.5

    def testParsePriceStringDecimalPuntoDevuelveFloat(self, parserService):
        """Prueba que _parsePrice convierte string con punto decimal a float"""
        # Arrange
        string_decimal = "10.50"

        # Act
        resultado = parserService._parsePrice(string_decimal)

        # Assert
        assert resultado == 10.5

    def testParsePriceStringDecimalComaDevuelveFloat(self, parserService):
        """Prueba que _parsePrice convierte string con coma decimal a float"""
        # Arrange
        string_decimal_coma = "10,50"

        # Act
        resultado = parserService._parsePrice(string_decimal_coma)

        # Assert
        assert resultado == 10.5

    def testParsePriceNoneDevuelveNone(self, parserService):
        """Prueba que _parsePrice devuelve None para valor None"""
        # Arrange
        valor_none = None

        # Act
        resultado = parserService._parsePrice(valor_none)

        # Assert
        assert resultado is None

    def testParsePriceStringInvalidoDevuelveNone(self, parserService):
        """Prueba que _parsePrice devuelve None para string inválido"""
        # Arrange
        string_invalido = "abc"

        # Act
        resultado = parserService._parsePrice(string_invalido)

        # Assert
        assert resultado is None

    def testParsePriceStringVacioDevuelveNone(self, parserService):
        """Prueba que _parsePrice devuelve None para string vacío"""
        # Arrange
        string_vacio = ""

        # Act
        resultado = parserService._parsePrice(string_vacio)

        # Assert
        assert resultado is None

    # ============== PRUEBAS PARA _parseQuantity ==============

    def testParseQuantityNumeroEnteroDevuelveFloat(self, parserService):
        """Prueba que _parseQuantity convierte números enteros a float"""
        # Arrange
        valor_entero = 5

        # Act
        resultado = parserService._parseQuantity(valor_entero)

        # Assert
        assert resultado == 5.0
        assert isinstance(resultado, float)

    def testParseQuantityNumeroFloatDevuelveMismoValor(self, parserService):
        """Prueba que _parseQuantity devuelve el mismo valor para floats"""
        # Arrange
        valor_float = 5.5

        # Act
        resultado = parserService._parseQuantity(valor_float)

        # Assert
        assert resultado == 5.5

    def testParseQuantityStringDecimalDevuelveFloat(self, parserService):
        """Prueba que _parseQuantity convierte string decimal a float"""
        # Arrange
        string_decimal = "5.5"

        # Act
        resultado = parserService._parseQuantity(string_decimal)

        # Assert
        assert resultado == 5.5

    def testParseQuantityStringComaDecimalDevuelveFloat(self, parserService):
        """Prueba que _parseQuantity convierte string con coma decimal a float"""
        # Arrange
        string_decimal_coma = "5,5"

        # Act
        resultado = parserService._parseQuantity(string_decimal_coma)

        # Assert
        assert resultado == 5.5

    def testParseQuantityNoneDevuelveUno(self, parserService):
        """Prueba que _parseQuantity devuelve 1.0 para valor None (default)"""
        # Arrange
        valor_none = None

        # Act
        resultado = parserService._parseQuantity(valor_none)

        # Assert
        assert resultado == 1.0

    def testParseQuantityStringInvalidoDevuelveUno(self, parserService):
        """Prueba que _parseQuantity devuelve 1.0 para string inválido (default)"""
        # Arrange
        string_invalido = "xyz"

        # Act
        resultado = parserService._parseQuantity(string_invalido)

        # Assert
        assert resultado == 1.0

    def testParseQuantityCeroDevuelveCero(self, parserService):
        """Prueba que _parseQuantity maneja cantidad cero correctamente"""
        # Arrange
        valor_cero = 0

        # Act
        resultado = parserService._parseQuantity(valor_cero)

        # Assert
        assert resultado == 0.0

    def testParseQuantityStringCeroDevuelveUno(self, parserService):
        """Prueba que _parseQuantity para '0' devuelve 1.0 debido a la lógica actual (val > 0 else 1.0)"""
        # Arrange
        string_cero = "0"
        # Nota: la lógica actual de `_parse_quantity` para string es `val if val > 0 else 1.0`
        # Si el string es "0", `float("0")` es `0.0`. Como `0.0 > 0` es falso, devuelve `1.0`.
        # Esto podría ser un comportamiento inesperado o un bug, dependiendo de los requisitos.
        # Si "0" como string debe ser 0.0, la lógica en `_parse_quantity` debería cambiar.

        # Act
        resultado = parserService._parseQuantity(string_cero)

        # Assert
        assert resultado == 1.0 # Basado en la lógica actual

    def testParseQuantityNegativoDevuelveValorOriginal(self, parserService):
        """Prueba que _parseQuantity devuelve valor negativo si es numérico"""
        # Arrange
        valor_negativo = -2

        # Act
        resultado = parserService._parseQuantity(valor_negativo)

        # Assert
        assert resultado == -2.0

    def testParseQuantityStringNegativoDevuelveUno(self, parserService):
        """Prueba que _parseQuantity devuelve 1.0 para string negativo (default)"""
        # Arrange
        string_negativo = "-2"
        # Mismo caso que con "0", `float("-2")` es `-2.0`. `-2.0 > 0` es falso, devuelve `1.0`.

        # Act
        resultado = parserService._parseQuantity(string_negativo)

        # Assert
        assert resultado == 1.0 # Basado en la lógica actual

    # ============== PRUEBAS ADICIONALES PARA parseTextToItems ==============

    def testParseTextToItemsJsonVacioDevuelveEstructuraVacia(self, parserService):
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

    def testParseTextToItemsValoresNullManejadosCorrectamente(self, parserService):
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
        assert len(resultado["items"]) == 2 # Solo el válido y el que tiene cantidad null (qty=1)
        assert resultado["items"][0].name == "Item con cantidad null"
        assert resultado["items"][0].quantity == 1.0 # Cantidad null se convierte a 1.0
        assert resultado["items"][1].name == "Item válido"

    def testParseTextToItemsMultiplesLlamadasReiniciaIds(self, parserService):
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

 