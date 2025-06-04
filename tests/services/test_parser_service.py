import pytest
import json
from unittest.mock import patch, Mock
import time
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

    class TestSimpleCases:
        """
        Pruebas unitarias para casos básicos y validaciones fundamentales de ParserService.
        """

        # ============== TESTS FOR parseTextToItems (Casos Simples) ==============

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
            assert resultado["is_ticket"] is True

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
            assert resultado["total"] == 20.00
            assert resultado["subtotal"] == 20.00
            assert resultado["tax"] is None
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
            })

            # Act
            resultado = parserService.parseTextToItems(json_con_subtotal_tax)

            # Assert
            assert resultado["total"] == 10.00
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
                    {"quantity": 1, "unit_price": 10.00},
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
                    {"description": "Item sin precio", "quantity": 1},
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
            assert resultado["is_ticket"] is True
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
            assert len(resultado["items"]) == 2
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
            assert resultado2["items"][0].id == 1

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
            })
            # Act
            resultado = parserService.parseTextToItems(json_con_total_tax)
            # Assert
            assert resultado["subtotal"] == 10.00
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
            })
            # Act
            resultado = parserService.parseTextToItems(json_con_total_items)
            # Assert
            assert resultado["subtotal"] == 20.00
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

    class TestComplexScenarios:
        """
        Pruebas de ParserService simulando escenarios realistas y casos más complejos.
        """

        # ============== ESCENARIOS REALISTAS (Anteriormente en _integration) ==============

        def test_parseTextToItemsRestaurant_completo_devuelveDatosCorrectos(self, parserService):
            """Simula una respuesta de IA para un ticket de restaurante completo"""
            # Arrange
            respuesta_gemini_restaurante = json.dumps({
                "items": [
                    {"description": "Café con leche", "quantity": 2, "unit_price": 1.80},
                    {"description": "Tostada integral", "quantity": 1, "unit_price": 3.50},
                    {"description": "Zumo naranja natural", "quantity": 1, "unit_price": 2.90},
                    {"description": "Croissant mantequilla", "quantity": 2, "unit_price": 2.20}
                ],
                "subtotal": 12.40,
                "tax": 1.24,
                "total": 13.64
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_gemini_restaurante)
            # Assert
            assert len(resultado["items"]) == 4
            assert resultado["items"][0].name == "Café con leche"
            assert resultado["items"][0].total_price == 3.60
            assert resultado["items"][3].name == "Croissant mantequilla"
            assert resultado["items"][3].total_price == 4.40
            assert resultado["subtotal"] == 12.40
            assert resultado["tax"] == 1.24
            assert resultado["total"] == 13.64

        def test_parseTextToItems_supermercadoConDescuentos_calculaCorrectamente(self, parserService):
            """Simula una respuesta de IA para un ticket de supermercado con descuentos"""
            # Arrange
            respuesta_gemini_supermercado = json.dumps({
                "items": [
                    {"description": "Pan integral 500g", "quantity": 1, "unit_price": 1.45},
                    {"description": "Leche desnatada 1L", "quantity": 2, "unit_price": 0.89},
                    {"description": "Manzanas Royal Gala 1kg", "quantity": 1, "unit_price": 2.35},
                    {"description": "Descuento socio -5%", "quantity": 1, "unit_price": -0.27}
                ],
                "subtotal": 4.95,
                "tax": 0.22,
                "total": 5.17
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_gemini_supermercado)
            # Assert
            assert len(resultado["items"]) == 4
            assert resultado["items"][1].total_price == 1.78
            assert resultado["items"][3].price == -0.27
            assert resultado["total"] == 5.17

        def test_parseTextToItems_farmaciaSinIva_manejaCorrectamente(self, parserService):
            """Simula una respuesta de IA para un ticket de farmacia (productos sin IVA)"""
            # Arrange
            respuesta_gemini_farmacia = json.dumps({
                "items": [
                    {"description": "Paracetamol 1g 20 comp", "quantity": 1, "unit_price": 2.85},
                    {"description": "Ibuprofeno 600mg 40 comp", "quantity": 1, "unit_price": 4.95},
                    {"description": "Vendas elásticas", "quantity": 2, "unit_price": 3.20}
                ],
                "subtotal": 14.20,
                "tax": 0.00,
                "total": 14.20
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_gemini_farmacia)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][2].total_price == 6.40
            assert resultado["tax"] == 0.00
            assert resultado["total"] == 14.20
            assert resultado["subtotal"] == 14.20

        def test_parseTextToItems_respuestaInconsistenteIa_calculaTotales(self, parserService):
            """Simula una respuesta inconsistente de IA donde faltan algunos totales"""
            # Arrange
            respuesta_gemini_inconsistente = json.dumps({
                "items": [
                    {"description": "Hamburguesa", "quantity": 1, "unit_price": 8.50},
                    {"description": "Patatas fritas", "quantity": 1, "unit_price": 3.50},
                    {"description": "Bebida", "quantity": 1, "unit_price": 2.00}
                ],
                "subtotal": 14.00,
                "tax": None,
                "total": None
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_gemini_inconsistente)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["subtotal"] == 14.00
            assert resultado["tax"] is None
            assert resultado["total"] == 14.00

        def test_parseTextToItems_conCaracteresEspeciales_manejaCorrectamente(self, parserService):
            """Prueba que maneja correctamente caracteres especiales en descripciones"""
            # Arrange
            respuesta_con_especiales = json.dumps({
                "items": [
                    {"description": "Café & Té especial", "quantity": 1, "unit_price": 2.50},
                    {"description": "Açaí bowl (100% natural)", "quantity": 1, "unit_price": 5.90},
                    {"description": "Sándwich jamón/queso", "quantity": 1, "unit_price": 4.20}
                ],
                "total": 12.60
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_con_especiales)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].name == "Café & Té especial"
            assert resultado["items"][1].name == "Açaí bowl (100% natural)"
            assert resultado["items"][2].name == "Sándwich jamón/queso"

        def test_parseTextToItems_decimalesDiferentesFormatos_normaliza(self, parserService):
            """Prueba que maneja diferentes formatos decimales correctamente"""
            # Arrange
            respuesta_decimales_mixtos = json.dumps({
                "items": [
                    {"description": "Item A", "quantity": "1,5", "unit_price": "2,30"},
                    {"description": "Item B", "quantity": 2.0, "unit_price": 1.75},
                    {"description": "Item C", "quantity": "3", "unit_price": "0.95"}
                ]
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_decimales_mixtos)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].quantity == 1.5
            assert resultado["items"][0].price == 2.30
            assert resultado["items"][0].total_price == 3.45
            assert resultado["items"][1].total_price == 3.50
            assert resultado["items"][2].total_price == 2.85

        def test_parseTextToItems_ticketGrande_rendimientoAceptable(self, parserService):
            """Prueba rendimiento con un ticket grande (muchos items)"""
            # Arrange
            items_grandes = []
            for i in range(50):
                items_grandes.append({
                    "description": f"Producto {i+1}",
                    "quantity": 1,
                    "unit_price": round(1.0 + (i * 0.1), 2)
                })
            respuesta_ticket_grande = json.dumps({
                "items": items_grandes,
                "total": 127.50 
            })
            # Act
            inicio = time.time()
            resultado = parserService.parseTextToItems(respuesta_ticket_grande)
            tiempo_transcurrido = time.time() - inicio
            # Assert
            assert len(resultado["items"]) == 50
            assert tiempo_transcurrido < 1.0
            assert resultado["items"][0].name == "Producto 1"
            assert resultado["items"][49].name == "Producto 50"
            # El ParserService utiliza el "total" del JSON si está presente.
            assert resultado["total"] == 127.50

        def test_parseTextToItems_jsonMalEstructurado_manejaGraciosamente(self, parserService):
            """Prueba manejo de JSON estructurado incorrectamente pero válido"""
            # Arrange
            json_mal_estructurado = json.dumps({
                "productos": [
                    {"description": "Item", "quantity": 1, "unit_price": 5.00}
                ],
                "items": [],
                "total": 5.00
            })
            # Act
            resultado = parserService.parseTextToItems(json_mal_estructurado)
            # Assert
            assert len(resultado["items"]) == 0
            assert resultado["total"] == 5.00 # El parser service debería tomar el total provisto si no hay items para calcularlo.

        def test_parseTextToItems_valoresExtremos_manejaCorrectamente(self, parserService):
            """Prueba manejo de valores extremos"""
            # Arrange
            respuesta_valores_extremos = json.dumps({
                "items": [
                    {"description": "Item barato", "quantity": 1, "unit_price": 0.01},
                    {"description": "Item caro", "quantity": 1, "unit_price": 999.99},
                    {"description": "Muchas unidades", "quantity": 100, "unit_price": 0.50}
                ]
                # No total, se calculará
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_valores_extremos)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].total_price == 0.01
            assert resultado["items"][1].total_price == 999.99
            assert resultado["items"][2].total_price == 50.00
            assert resultado["total"] == (0.01 + 999.99 + 50.00) # 1050.00

        def test_parseTextToItems_itemsDuplicados_mantieneTodos(self, parserService):
            """Prueba que mantiene items duplicados con IDs diferentes"""
            # Arrange
            respuesta_duplicados = json.dumps({
                "items": [
                    {"description": "Café", "quantity": 1, "unit_price": 2.50},
                    {"description": "Café", "quantity": 1, "unit_price": 2.50},
                    {"description": "Café", "quantity": 1, "unit_price": 2.50}
                ]
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_duplicados)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].id == 1
            assert resultado["items"][1].id == 2
            assert resultado["items"][2].id == 3
            assert all(item.name == "Café" for item in resultado["items"])
            assert all(item.price == 2.50 for item in resultado["items"])

        def test_parseTextToItems_camposAdicionales_ignorados(self, parserService):
            """Prueba que ignora campos adicionales no reconocidos"""
            # Arrange
            respuesta_campos_extra = json.dumps({
                "items": [
                    {
                        "description": "Item normal",
                        "quantity": 1,
                        "unit_price": 5.00,
                        "categoria": "bebidas",
                        "descuento_aplicado": True,
                        "codigo_producto": "ABC123"
                    }
                ],
                "metodo_pago": "efectivo",
                "cajero": "Juan",
                "total": 5.00
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_campos_extra)
            # Assert
            assert len(resultado["items"]) == 1
            assert resultado["items"][0].name == "Item normal"
            assert resultado["items"][0].price == 5.00
            assert resultado["total"] == 5.00

        def test_parseTextToItems_totalesConPrecisionDecimal_manejaCorrectamente(self, parserService):
            """Prueba manejo correcto de precisión decimal en totales"""
            # Arrange
            respuesta_precision_decimal = json.dumps({
                "items": [
                    {"description": "Item 1", "quantity": 3, "unit_price": 1.333333}, # total_price = 3.999999
                    {"description": "Item 2", "quantity": 2, "unit_price": 2.666667}  # total_price = 5.333334
                ],
                "subtotal": 9.333333, # Suma de unit_prices * quantity no redondeados
                "tax": 0.933333,
                "total": 10.266666  # Suma de subtotal y tax
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_precision_decimal)
            # Assert
            assert len(resultado["items"]) == 2
            # El Item model redondea total_price a 2 decimales en su __post_init__
            assert resultado["items"][0].total_price == 4.00  # round(3 * 1.333333, 2) -> round(3.999999, 2) = 4.00
            assert resultado["items"][1].total_price == 5.33  # round(2 * 2.666667, 2) -> round(5.333334, 2) = 5.33
            
            # Los totales del ticket (subtotal, tax, total) se toman del JSON si están presentes.
            # El ParserService los usa directamente.
            assert resultado["subtotal"] == 9.333333
            assert resultado["tax"] == 0.933333
            assert resultado["total"] == 10.266666

        def test_parseTextToItems_itemsConCantidadDecimal_calculaCorrectamente(self, parserService):
            """Prueba cálculo correcto con cantidades decimales"""
            # Arrange
            respuesta_cantidad_decimal = json.dumps({
                "items": [
                    {"description": "Jamón (por kg)", "quantity": 0.5, "unit_price": 12.50}, # 6.25
                    {"description": "Queso (por kg)", "quantity": 0.25, "unit_price": 18.00},# 4.50
                    {"description": "Pan", "quantity": 1.5, "unit_price": 2.30} # 3.45
                ]
                # Total: 6.25 + 4.50 + 3.45 = 14.20
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_cantidad_decimal)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].total_price == 6.25
            assert resultado["items"][1].total_price == 4.50
            assert resultado["items"][2].total_price == 3.45
            assert resultado["total"] == 14.20

        def test_ParseTextToItemsSupermercadoConDescuentosCalculaCorrectamente(self, parserService): # Nombre del test original de _integration
            """Prueba cálculo correcto con descuentos en supermercado"""
            # Arrange
            respuesta_supermercado = json.dumps({
                "items": [
                    {"description": "Leche", "quantity": 1, "unit_price": 1.20},
                    {"description": "Pan", "quantity": 1, "unit_price": 0.80},
                    {"description": "Descuento", "quantity": 1, "unit_price": -0.50}
                ],
                "subtotal": 1.50, # 1.20 + 0.80 - 0.50 = 1.50
                "tax": 0.00,
                "total": 1.50
            })
            # Act
            resultado = parserService.parseTextToItems(respuesta_supermercado)
            # Assert
            assert len(resultado["items"]) == 3
            assert resultado["items"][0].total_price == 1.20
            assert resultado["items"][1].total_price == 0.80
            assert resultado["items"][2].total_price == -0.50
            assert resultado["total"] == 1.50
            assert resultado["is_ticket"] is True
            assert resultado["error_message"] is None

 