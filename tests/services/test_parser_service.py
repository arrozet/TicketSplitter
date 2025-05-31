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

    def parseTextToItems_jsonValido_devuelveDatosCorrectos(self, parserService):
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
        assert resultado["items"][0].description == "Café"
        assert resultado["items"][0].quantity == 1
        assert resultado["items"][0].unit_price == 2.50
        assert resultado["items"][0].total_price == 2.50
        assert resultado["items"][1].description == "Tostada"
        assert resultado["items"][1].quantity == 2
        assert resultado["items"][1].unit_price == 3.00
        assert resultado["items"][1].total_price == 6.00
        assert resultado["subtotal"] == 8.50
        assert resultado["tax"] == 0.85
        assert resultado["total"] == 9.35
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_jsonMalformado_devuelveDatosVacios(self, parserService):
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
        assert resultado["is_ticket"] is False
        assert "Error al parsear JSON" in resultado["error_message"]

    def parseTextToItems_sinTotales_calculaTotalAutomaticamente(self, parserService):
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
        assert resultado["tax"] == 0.00
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_conSubtotalYTax_calculaTotal(self, parserService):
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

    def parseTextToItems_conTotalYTax_calculaSubtotal(self, parserService):
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

    def parseTextToItems_itemsSinDescripcion_sonIgnorados(self, parserService):
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
        assert resultado["items"][0].description == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_itemsSinPrecio_sonIgnorados(self, parserService):
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
        assert resultado["items"][0].description == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_precioCero_esValido(self, parserService):
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
        assert resultado["items"][0].unit_price == 0.0
        assert resultado["items"][0].total_price == 0.0
        assert resultado["items"][1].unit_price == 5.00
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_jsonVacio_devuelveEstructuraVacia(self, parserService):
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
        assert resultado["is_ticket"] is False
        assert "No se encontraron items" in resultado["error_message"]

    def parseTextToItems_valoresNull_manejadosCorrectamente(self, parserService):
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
        assert len(resultado["items"]) == 1  # Solo el item válido
        assert resultado["items"][0].description == "Item válido"
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None

    def parseTextToItems_variosIds_asignaIdsSecuenciales(self, parserService):
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

    def parseTextToItems_multiplesLlamadas_reiniciaIds(self, parserService):
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

 