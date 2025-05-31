import pytest
import json
from app.services.parser_service import ParserService


class TestParserServiceIntegration:
    """
    Pruebas de integración para ParserService simulando escenarios realistas.
    Usa mocks para evitar llamadas reales a APIs de IA.
    """

    @pytest.fixture
    def parserService(self):
        """Fixture para obtener una instancia del ParserService"""
        return ParserService()

    # ============== ESCENARIOS REALISTAS ==============

    def parseTextToItemsRestaurant_completo_devuelveDatosCorrectos(self, parserService):
        """Simula una respuesta de IA para un ticket de restaurante completo"""
        # Arrange - Simula respuesta de Gemini para un restaurante
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
        assert resultado["items"][0].total_price == 3.60  # 2 * 1.80
        assert resultado["items"][3].name == "Croissant mantequilla"
        assert resultado["items"][3].total_price == 4.40  # 2 * 2.20
        assert resultado["subtotal"] == 12.40
        assert resultado["tax"] == 1.24
        assert resultado["total"] == 13.64

    def parseTextToItems_supermercadoConDescuentos_calculaCorrectamente(self, parserService):
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
        assert resultado["items"][1].total_price == 1.78  # 2 * 0.89
        assert resultado["items"][3].price == -0.27  # Descuento como precio negativo
        assert resultado["total"] == 5.17

    def parseTextToItems_farmaciaSinIva_manejaCorrectamente(self, parserService):
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
        assert resultado["items"][2].total_price == 6.40  # 2 * 3.20
        assert resultado["tax"] == 0.00
        assert resultado["total"] == 14.20
        assert resultado["subtotal"] == 14.20

    def parseTextToItems_respuestaInconsistenteIa_calculaTotales(self, parserService):
        """Simula una respuesta inconsistente de IA donde faltan algunos totales"""
        # Arrange
        respuesta_gemini_inconsistente = json.dumps({
            "items": [
                {"description": "Hamburguesa", "quantity": 1, "unit_price": 8.50},
                {"description": "Patatas fritas", "quantity": 1, "unit_price": 3.50},
                {"description": "Bebida", "quantity": 1, "unit_price": 2.00}
            ],
            "subtotal": 14.00,
            "tax": None,  # IA no proporcionó tax
            "total": None  # IA no proporcionó total
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_gemini_inconsistente)

        # Assert
        assert len(resultado["items"]) == 3
        assert resultado["subtotal"] == 14.00
        assert resultado["tax"] is None
        assert resultado["total"] == 14.00  # Calculado automáticamente

    def parseTextToItems_conCaracteresEspeciales_manejaCorrectamente(self, parserService):
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

    def parseTextToItems_decimalesDiferentesFormatos_normaliza(self, parserService):
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
        assert resultado["items"][0].total_price == 3.45  # 1.5 * 2.30
        assert resultado["items"][1].total_price == 3.50  # 2.0 * 1.75
        assert resultado["items"][2].total_price == 2.85  # 3.0 * 0.95

    def parseTextToItems_ticketGrande_rendimientoAceptable(self, parserService):
        """Prueba rendimiento con un ticket grande (muchos items)"""
        # Arrange - Ticket con 50 items
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
        import time
        inicio = time.time()
        resultado = parserService.parseTextToItems(respuesta_ticket_grande)
        tiempo_transcurrido = time.time() - inicio

        # Assert
        assert len(resultado["items"]) == 50
        assert tiempo_transcurrido < 1.0  # Debe procesarse en menos de 1 segundo
        assert resultado["items"][0].name == "Producto 1"
        assert resultado["items"][49].name == "Producto 50"

    def parseTextToItems_jsonMalEstructurado_manejaGraciosamente(self, parserService):
        """Prueba manejo de JSON estructurado incorrectamente pero válido"""
        # Arrange
        json_mal_estructurado = json.dumps({
            "productos": [  # Key incorrecta (debería ser "items")
                {"description": "Item", "quantity": 1, "unit_price": 5.00}
            ],
            "items": [],  # Array vacío
            "total": 5.00
        })

        # Act
        resultado = parserService.parseTextToItems(json_mal_estructurado)

        # Assert
        assert len(resultado["items"]) == 0  # No encuentra items en el array correcto
        assert resultado["total"] == 5.00

    def parseTextToItems_valoresExtremos_manejaCorrectamente(self, parserService):
        """Prueba manejo de valores extremos"""
        # Arrange
        respuesta_valores_extremos = json.dumps({
            "items": [
                {"description": "Item barato", "quantity": 1, "unit_price": 0.01},
                {"description": "Item caro", "quantity": 1, "unit_price": 999.99},
                {"description": "Muchas unidades", "quantity": 100, "unit_price": 0.50}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_valores_extremos)

        # Assert
        assert len(resultado["items"]) == 3
        assert resultado["items"][0].total_price == 0.01
        assert resultado["items"][1].total_price == 999.99
        assert resultado["items"][2].total_price == 50.00  # 100 * 0.50
        assert resultado["total"] == 1050.00

    def parseTextToItems_itemsDuplicados_mantieneTodos(self, parserService):
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
        # Todos tienen el mismo nombre y precio pero diferentes IDs
        assert all(item.name == "Café" for item in resultado["items"])
        assert all(item.price == 2.50 for item in resultado["items"])

    def parseTextToItems_camposAdicionales_ignorados(self, parserService):
        """Prueba que ignora campos adicionales no reconocidos"""
        # Arrange
        respuesta_campos_extra = json.dumps({
            "items": [
                {
                    "description": "Item normal",
                    "quantity": 1,
                    "unit_price": 5.00,
                    "categoria": "bebidas",  # Campo extra
                    "descuento_aplicado": True,  # Campo extra
                    "codigo_producto": "ABC123"  # Campo extra
                }
            ],
            "metodo_pago": "efectivo",  # Campo extra
            "cajero": "Juan",  # Campo extra
            "total": 5.00
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_campos_extra)

        # Assert
        assert len(resultado["items"]) == 1
        assert resultado["items"][0].name == "Item normal"
        assert resultado["items"][0].price == 5.00
        assert resultado["total"] == 5.00
        # Los campos extra son ignorados silenciosamente

    def parseTextToItems_totalesConPrecisionDecimal_manejaCorrectamente(self, parserService):
        """Prueba manejo correcto de precisión decimal en totales"""
        # Arrange
        respuesta_precision_decimal = json.dumps({
            "items": [
                {"description": "Item 1", "quantity": 3, "unit_price": 1.333333},
                {"description": "Item 2", "quantity": 2, "unit_price": 2.666667}
            ],
            "subtotal": 9.333333,
            "tax": 0.933333,
            "total": 10.266666
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_precision_decimal)

        # Assert
        assert len(resultado["items"]) == 2
        # Los totales de items se redondean a 2 decimales
        assert resultado["items"][0].total_price == 4.00  # round(3 * 1.333333, 2)
        assert resultado["items"][1].total_price == 5.33  # round(2 * 2.666667, 2)
        # Los totales generales mantienen la precisión original
        assert resultado["subtotal"] == 9.333333
        assert resultado["tax"] == 0.933333
        assert resultado["total"] == 10.266666

    def parseTextToItems_itemsConCantidadDecimal_calculaCorrectamente(self, parserService):
        """Prueba cálculo correcto con cantidades decimales"""
        # Arrange
        respuesta_cantidad_decimal = json.dumps({
            "items": [
                {"description": "Jamón (por kg)", "quantity": 0.5, "unit_price": 12.50},
                {"description": "Queso (por kg)", "quantity": 0.25, "unit_price": 18.00},
                {"description": "Pan", "quantity": 1.5, "unit_price": 2.30}
            ]
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_cantidad_decimal)

        # Assert
        assert len(resultado["items"]) == 3
        assert resultado["items"][0].total_price == 6.25   # 0.5 * 12.50
        assert resultado["items"][1].total_price == 4.50   # 0.25 * 18.00
        assert resultado["items"][2].total_price == 3.45   # 1.5 * 2.30
        assert resultado["total"] == 14.20  # Suma de todos los totales

    def testParseTextToItemsSupermercadoConDescuentosCalculaCorrectamente(self, parserService):
        """Prueba cálculo correcto con descuentos en supermercado"""
        # Arrange
        respuesta_supermercado = json.dumps({
            "items": [
                {"description": "Leche", "quantity": 1, "unit_price": 1.20},
                {"description": "Pan", "quantity": 1, "unit_price": 0.80},
                {"description": "Descuento", "quantity": 1, "unit_price": -0.50}
            ],
            "subtotal": 1.50,
            "tax": 0.00,
            "total": 1.50
        })

        # Act
        resultado = parserService.parseTextToItems(respuesta_supermercado)

        # Assert
        assert len(resultado["items"]) == 3
        assert resultado["items"][0].total_price == 1.20   # 1 * 1.20
        assert resultado["items"][1].total_price == 0.80   # 1 * 0.80
        assert resultado["items"][2].total_price == -0.50  # 1 * -0.50
        assert resultado["total"] == 1.50  # 1.20 + 0.80 - 0.50
        assert resultado["is_ticket"] is True
        assert resultado["error_message"] is None 