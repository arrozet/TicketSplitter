# Testing del ParserService

Este directorio contiene las pruebas unitarias e integración para el `ParserService`, el servicio responsable de parsear respuestas JSON de IA y convertirlas en objetos `Item`.

## Características Principales

- ✅ **100% uso de mocks** - No realizamos llamadas reales a APIs de IA
- ✅ **Patrón AAA** - Todas las pruebas siguen Arrange-Act-Assert
- ✅ **Nomenclatura clara** - Formato `metodo_prueba_resultado`
- ✅ **Cobertura completa** - Casos exitosos, errores y edge cases

## Archivos de Pruebas

### `test_parser_service.py`
Pruebas unitarias focalizadas en métodos específicos:

- **parse_text_to_items**: 10 pruebas
  - JSON válido, malformado, cálculo automático de totales
  - Manejo de campos faltantes, valores null, IDs secuenciales
  
- **_parse_price**: 7 pruebas
  - Conversión de números, strings, decimales con coma
  - Manejo de valores None e inválidos
  
- **_parse_quantity**: 8 pruebas
  - Conversión de cantidades, valores por defecto
  - Validación de valores negativos y cero

### `test_parser_service_integration.py`
Pruebas de integración con escenarios realistas:

- **Escenarios de negocio**: Restaurante, supermercado, farmacia
- **Casos complejos**: Descuentos, caracteres especiales, decimales
- **Rendimiento**: Tickets grandes (50+ items)
- **Robustez**: Valores extremos, JSON mal estructurado

## Cómo Ejecutar las Pruebas

### Prerequisitos

```bash
# Instalar dependencias
pip install pytest pytest-mock

# Verificar que el modelo Item existe
# El archivo app/models/item.py debe existir con la clase Item
```

### Ejecutar Todas las Pruebas

```bash
# Desde la raíz del proyecto
pytest tests/services/ -v

# Solo pruebas del ParserService
pytest tests/services/test_parser_service.py -v
pytest tests/services/test_parser_service_integration.py -v
```

### Ejecutar Pruebas Específicas

```bash
# Una prueba específica
pytest tests/services/test_parser_service.py::TestParserService::test_parse_text_to_items_json_valido_devuelve_items_parseados -v

# Todas las pruebas de un método
pytest tests/services/test_parser_service.py -k "parse_price" -v

# Pruebas de integración
pytest tests/services/test_parser_service_integration.py -k "restaurante" -v
```

### Ejecutar con Cobertura

```bash
# Instalar coverage
pip install pytest-cov

# Ejecutar con reporte de cobertura
pytest tests/services/ --cov=app.services.parser_service --cov-report=html

# Ver reporte detallado
pytest tests/services/ --cov=app.services.parser_service --cov-report=term-missing
```

## Estructura de las Pruebas

### Patrón AAA (Arrange-Act-Assert)

```python
def test_parse_price_string_decimal_punto_devuelve_float(self, parser_service):
    """Prueba que _parse_price convierte string con punto decimal a float"""
    # Arrange
    string_decimal = "10.50"

    # Act
    resultado = parser_service._parse_price(string_decimal)

    # Assert
    assert resultado == 10.5
```

### Nomenclatura de Pruebas

Formato: `test_{metodo}_{escenario}_{resultado_esperado}`

- `test_parse_text_to_items_json_valido_devuelve_items_parseados`
- `test_parse_price_string_invalido_devuelve_none`
- `test_parse_quantity_cero_devuelve_uno`

## Datos de Prueba

### JSON de Ejemplo Simulando Respuesta de IA

```json
{
  "items": [
    {"description": "Café", "quantity": 1, "unit_price": 2.50},
    {"description": "Tostada", "quantity": 2, "unit_price": 3.00}
  ],
  "subtotal": 8.50,
  "tax": 0.85,
  "total": 9.35
}
```

### Escenarios Cubiertos

- ✅ Tickets de restaurante con múltiples items
- ✅ Supermercado con descuentos (precios negativos)
- ✅ Farmacia sin IVA
- ✅ Respuestas inconsistentes de IA
- ✅ Caracteres especiales en descripciones
- ✅ Diferentes formatos decimales (punto/coma)
- ✅ Tickets grandes (50+ items)
- ✅ Valores extremos (0.01€ a 999.99€)
- ✅ Items duplicados
- ✅ Cantidades decimales (0.5 kg)

## Verificación de Funcionalidad

Las pruebas verifican:

1. **Parseo correcto** del JSON de respuesta de IA
2. **Cálculo automático** de totales cuando faltan
3. **Manejo de errores** gracioso (JSON malformado)
4. **Validación de datos** (precios negativos, cantidades cero)
5. **Asignación secuencial** de IDs a items
6. **Rendimiento aceptable** (< 1 segundo para 50 items)

## Integración Continua

Estas pruebas están diseñadas para ejecutarse en pipelines de CI/CD:

```yaml
# Ejemplo para GitHub Actions
- name: Run Parser Service Tests
  run: |
    pytest tests/services/ -v --tb=short
    pytest tests/services/ --cov=app.services.parser_service --cov-fail-under=95
```

## Troubleshooting

### Error: ModuleNotFoundError

```bash
# Asegurar que PYTHONPATH incluye la raíz del proyecto
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/services/
```

### Error: Item model not found

```bash
# Verificar que existe app/models/item.py
ls app/models/item.py

# El modelo debe tener esta estructura mínima:
class Item:
    def __init__(self, id, name, quantity, price, total_price):
        self.id = id
        self.name = name
        self.quantity = quantity
        self.price = price
        self.total_price = total_price
```

## Mantenimiento

Para añadir nuevas pruebas:

1. Seguir la nomenclatura establecida
2. Usar el patrón AAA
3. Incluir docstring descriptivo
4. Mockear cualquier dependencia externa
5. Verificar que la prueba falla antes de implementar la funcionalidad 