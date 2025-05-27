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
    def parser_service(self):
        """Fixture para obtener una instancia del ParserService"""
        return ParserService()

    # ============== PRUEBAS PARA parse_text_to_items ==============

    def test_parse_text_to_items_json_valido_devuelve_items_parseados(self, parser_service):
        """Prueba que parse_text_to_items con JSON válido devuelve items correctamente parseados"""
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
        resultado = parser_service.parse_text_to_items(json_valido)

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

    def test_parse_text_to_items_json_malformado_devuelve_datos_vacios(self, parser_service):
        """Prueba que parse_text_to_items con JSON malformado devuelve datos vacíos"""
        # Arrange
        json_malformado = '{"items": [{"description": "Café", "quantity": 1'  # JSON incompleto

        # Act
        resultado = parser_service.parse_text_to_items(json_malformado)

        # Assert
        assert len(resultado["items"]) == 0
        assert resultado["subtotal"] is None
        assert resultado["tax"] is None
        assert resultado["total"] is None
        assert resultado["raw_text"] == json_malformado

    def test_parse_text_to_items_sin_totales_calcula_total_automaticamente(self, parser_service):
        """Prueba que parse_text_to_items sin totales calcula el total automáticamente"""
        # Arrange
        json_sin_totales = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 2, "unit_price": 5.00},
                {"description": "Item 2", "quantity": 1, "unit_price": 10.00}
            ]
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_sin_totales)

        # Assert
        assert len(resultado["items"]) == 2
        assert resultado["total"] == 20.00  # (2 * 5.00) + (1 * 10.00)
        assert resultado["subtotal"] == 20.00

    def test_parse_text_to_items_con_subtotal_y_tax_calcula_total(self, parser_service):
        """Prueba que parse_text_to_items con subtotal y tax calcula el total"""
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
        resultado = parser_service.parse_text_to_items(json_con_subtotal_tax)

        # Assert
        # El servicio calcula total basado en items cuando subtotal+tax no coincide
        assert resultado["total"] == 10.00  # Total calculado de items (1 * 10.00)
        assert resultado["subtotal"] == 10.00
        assert resultado["tax"] == 1.00

    def test_parse_text_to_items_con_total_y_tax_calcula_subtotal(self, parser_service):
        """Prueba que parse_text_to_items con total y tax calcula el subtotal"""
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
        resultado = parser_service.parse_text_to_items(json_con_total_tax)

        # Assert
        assert resultado["subtotal"] == 10.00
        assert resultado["tax"] == 1.00
        assert resultado["total"] == 11.00

    def test_parse_text_to_items_items_sin_descripcion_son_ignorados(self, parser_service):
        """Prueba que parse_text_to_items ignora items sin descripción"""
        # Arrange
        json_con_item_sin_descripcion = json.dumps({
            "items": [
                {"quantity": 1, "unit_price": 10.00},  # Sin description
                {"description": "Item válido", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_con_item_sin_descripcion)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].name == "Item válido"

    def test_parse_text_to_items_items_sin_precio_son_ignorados(self, parser_service):
        """Prueba que parse_text_to_items ignora items sin precio unitario"""
        # Arrange
        json_con_item_sin_precio = json.dumps({
            "items": [
                {"description": "Item sin precio", "quantity": 1},  # Sin unit_price
                {"description": "Item válido", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_con_item_sin_precio)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].name == "Item válido"

    def test_parse_text_to_items_asigna_ids_secuenciales(self, parser_service):
        """Prueba que parse_text_to_items asigna IDs secuenciales a los items"""
        # Arrange
        json_con_multiples_items = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 1, "unit_price": 1.00},
                {"description": "Item 2", "quantity": 1, "unit_price": 2.00},
                {"description": "Item 3", "quantity": 1, "unit_price": 3.00}
            ]
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_con_multiples_items)

        # Assert
        assert resultado["items"][0].id == 1
        assert resultado["items"][1].id == 2
        assert resultado["items"][2].id == 3

    def test_parse_text_to_items_precio_cero_es_valido(self, parser_service):
        """Prueba que parse_text_to_items acepta items con precio cero"""
        # Arrange
        json_con_precio_cero = json.dumps({
            "items": [
                {"description": "Item gratis", "quantity": 1, "unit_price": 0.0},
                {"description": "Item normal", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_con_precio_cero)

        # Assert
        assert len(resultado["items"]) == 2
        assert resultado["items"][0].price == 0.0
        assert resultado["items"][0].total_price == 0.0
        assert resultado["items"][1].price == 5.00

    # ============== PRUEBAS PARA _parse_price ==============

    def test_parse_price_numero_entero_devuelve_float(self, parser_service):
        """Prueba que _parse_price convierte números enteros a float"""
        # Arrange
        valor_entero = 10

        # Act
        resultado = parser_service._parse_price(valor_entero)

        # Assert
        assert resultado == 10.0
        assert isinstance(resultado, float)

    def test_parse_price_numero_float_devuelve_mismo_valor(self, parser_service):
        """Prueba que _parse_price devuelve el mismo valor para floats"""
        # Arrange
        valor_float = 10.5

        # Act
        resultado = parser_service._parse_price(valor_float)

        # Assert
        assert resultado == 10.5

    def test_parse_price_string_decimal_punto_devuelve_float(self, parser_service):
        """Prueba que _parse_price convierte string con punto decimal a float"""
        # Arrange
        string_decimal = "10.50"

        # Act
        resultado = parser_service._parse_price(string_decimal)

        # Assert
        assert resultado == 10.5

    def test_parse_price_string_decimal_coma_devuelve_float(self, parser_service):
        """Prueba que _parse_price convierte string con coma decimal a float"""
        # Arrange
        string_decimal_coma = "10,50"

        # Act
        resultado = parser_service._parse_price(string_decimal_coma)

        # Assert
        assert resultado == 10.5

    def test_parse_price_none_devuelve_none(self, parser_service):
        """Prueba que _parse_price devuelve None para valor None"""
        # Arrange
        valor_none = None

        # Act
        resultado = parser_service._parse_price(valor_none)

        # Assert
        assert resultado is None

    def test_parse_price_string_invalido_devuelve_none(self, parser_service):
        """Prueba que _parse_price devuelve None para string inválido"""
        # Arrange
        string_invalido = "abc"

        # Act
        resultado = parser_service._parse_price(string_invalido)

        # Assert
        assert resultado is None

    def test_parse_price_string_vacio_devuelve_none(self, parser_service):
        """Prueba que _parse_price devuelve None para string vacío"""
        # Arrange
        string_vacio = ""

        # Act
        resultado = parser_service._parse_price(string_vacio)

        # Assert
        assert resultado is None

    # ============== PRUEBAS PARA _parse_quantity ==============

    def test_parse_quantity_numero_entero_devuelve_float(self, parser_service):
        """Prueba que _parse_quantity convierte números enteros a float"""
        # Arrange
        valor_entero = 2

        # Act
        resultado = parser_service._parse_quantity(valor_entero)

        # Assert
        assert resultado == 2.0
        assert isinstance(resultado, float)

    def test_parse_quantity_numero_float_devuelve_mismo_valor(self, parser_service):
        """Prueba que _parse_quantity devuelve el mismo valor para floats"""
        # Arrange
        valor_float = 2.5

        # Act
        resultado = parser_service._parse_quantity(valor_float)

        # Assert
        assert resultado == 2.5

    def test_parse_quantity_string_decimal_devuelve_float(self, parser_service):
        """Prueba que _parse_quantity convierte string decimal a float"""
        # Arrange
        string_decimal = "1.5"

        # Act
        resultado = parser_service._parse_quantity(string_decimal)

        # Assert
        assert resultado == 1.5

    def test_parse_quantity_string_coma_decimal_devuelve_float(self, parser_service):
        """Prueba que _parse_quantity convierte string con coma decimal a float"""
        # Arrange
        string_coma = "2,5"

        # Act
        resultado = parser_service._parse_quantity(string_coma)

        # Assert
        assert resultado == 2.5

    def test_parse_quantity_none_devuelve_uno(self, parser_service):
        """Prueba que _parse_quantity devuelve 1.0 para valor None"""
        # Arrange
        valor_none = None

        # Act
        resultado = parser_service._parse_quantity(valor_none)

        # Assert
        assert resultado == 1.0

    def test_parse_quantity_string_invalido_devuelve_uno(self, parser_service):
        """Prueba que _parse_quantity devuelve 1.0 para string inválido"""
        # Arrange
        string_invalido = "abc"

        # Act
        resultado = parser_service._parse_quantity(string_invalido)

        # Assert
        assert resultado == 1.0

    def test_parse_quantity_cero_devuelve_cero(self, parser_service):
        """Prueba que _parse_quantity devuelve 0.0 para valor cero (int/float)"""
        # Arrange
        valor_cero = 0

        # Act
        resultado = parser_service._parse_quantity(valor_cero)

        # Assert
        assert resultado == 0.0

    def test_parse_quantity_string_cero_devuelve_uno(self, parser_service):
        """Prueba que _parse_quantity devuelve 1.0 para string "0" """
        # Arrange
        string_cero = "0"

        # Act
        resultado = parser_service._parse_quantity(string_cero)

        # Assert
        assert resultado == 1.0

    def test_parse_quantity_negativo_devuelve_valor_original(self, parser_service):
        """Prueba que _parse_quantity devuelve el valor negativo original para int/float"""
        # Arrange
        valor_negativo = -1

        # Act
        resultado = parser_service._parse_quantity(valor_negativo)

        # Assert
        assert resultado == -1.0  # Los valores negativos int/float se mantienen

    def test_parse_quantity_string_negativo_devuelve_uno(self, parser_service):
        """Prueba que _parse_quantity devuelve 1.0 para string negativo"""
        # Arrange
        string_negativo = "-1"

        # Act
        resultado = parser_service._parse_quantity(string_negativo)

        # Assert
        assert resultado == 1.0  # Los strings negativos se convierten a 1.0

    # ============== PRUEBAS DE INTEGRACIÓN ==============

    def test_parse_text_to_items_json_vacio_devuelve_estructura_vacia(self, parser_service):
        """Prueba que parse_text_to_items con JSON vacío devuelve estructura vacía"""
        # Arrange
        json_vacio = json.dumps({})

        # Act
        resultado = parser_service.parse_text_to_items(json_vacio)

        # Assert
        assert len(resultado["items"]) == 0
        assert resultado["subtotal"] is None
        assert resultado["tax"] is None
        assert resultado["total"] is None

    def test_parse_text_to_items_valores_null_manejados_correctamente(self, parser_service):
        """Prueba que parse_text_to_items maneja valores null correctamente"""
        # Arrange
        json_con_nulls = json.dumps({
            "items": [
                {"description": "Item", "quantity": None, "unit_price": 5.00}
            ],
            "subtotal": None,
            "tax": None,
            "total": None
        })

        # Act
        resultado = parser_service.parse_text_to_items(json_con_nulls)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].quantity == 1.0  # Valor por defecto
        # El servicio calcula automáticamente subtotal cuando hay items y no hay total
        assert resultado["subtotal"] == 5.0  # Calculado de items (1.0 * 5.00)
        assert resultado["tax"] is None

    def test_parse_text_to_items_multiples_llamadas_reinicia_ids(self, parser_service):
        """Prueba que parse_text_to_items reinicia los IDs en múltiples llamadas"""
        # Arrange
        json_simple = json.dumps({
            "items": [
                {"description": "Item", "quantity": 1, "unit_price": 5.00}
            ]
        })

        # Act
        resultado1 = parser_service.parse_text_to_items(json_simple)
        resultado2 = parser_service.parse_text_to_items(json_simple)

        # Assert
        assert resultado1["items"][0].id == 1
        assert resultado2["items"][0].id == 1  # Se reinicia en cada llamada 