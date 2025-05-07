import re
from typing import List, Dict, Any, Optional
from app.models.item import Item, ItemCreate # Asumiendo que ItemCreate y Item están definidos

class ParserService:
    def __init__(self):
        # Patrones de expresiones regulares para extraer información.
        # IMPORTANTE: Estos son ejemplos y probablemente necesiten ser ajustados y ampliados
        # significativamente para cubrir la diversidad de formatos de tickets reales.
        # Para una solución robusta, se requerirían técnicas más avanzadas
        # (ej. modelos de ML entrenados para extracción de entidades en tickets).
        # Formato: (nombre_del_patron, regex_ compilado)
        self.item_patterns = [
            # Patrón 1: "(cantidad) (unidad) NOMBRE DEL PRODUCTO ..... PRECIO"
            # Ejemplo: "2 KG MANZANAS GOLDEN ..... 3.50"
            #          "1 UD PAN BARRA ........ 0.80"
            #          "CERVEZA ESPECIAL ........ 2.50" (cantidad y unidad implícitas como 1 UD)
            (
                "qty_unit_name_price",
                re.compile(
                    r"^(?:(\d+[,.]?\d*)\s*(?:uds?|kg|gr|l|ml|und|unidades|unidad|u\.)?\s+)?"
                    r"([A-ZÁÉÍÓÚÑÇa-záéíóúñç0-9\s\-/&'\.+]+?)"
                    r"\s*(?:\.{2,}|\s{2,})\s*"
                    r"(\d+[,.]\d{1,2})\s*€?$",
                    re.IGNORECASE
                )
            ),
            # Patrón 2: "NOMBRE DEL PRODUCTO ..... CANTIDAD x PRECIO_UNITARIO ..... PRECIO_TOTAL"
            # Ejemplo: "COCA COLA ZERO ...... 2 x 1.50 ...... 3.00"
            (
                "name_qty_x_price_totalprice",
                re.compile(
                    r"^([A-ZÁÉÍÓÚÑÇa-záéíóúñç0-9\s\-/&'\.+]+?)"
                    r"\s*(?:\.{2,}|\s{2,})\s*"
                    r"(\d+[,.]?\d*)\s*x\s*(\d+[,.]\d{1,2})\s*€?"
                    r"\s*(?:\.{2,}|\s{2,})\s*"
                    r"(\d+[,.]\d{1,2})\s*€?$",
                    re.IGNORECASE
                )
            ),
            # Patrón 3: Líneas que solo contienen un precio (podría ser subtotal, total, etc.)
            # Ejemplo: "TOTAL: 25,50"
            #          "SUBTOTAL 20.00"
            (
                "total_keywords",
                re.compile(r"^(TOTAL|SUBTOTAL|SUMA|IVA|IMPUESTOS|DESCUENTO|DTO\.?|PROPINA|SERVICIO)\b.*\s+(\d+[,.]\d{1,2})\s*€?$", re.IGNORECASE)
            )
        ]
        self.next_item_id = 1

    def _parse_price(self, price_str: str) -> float:
        """Convierte un string de precio (ej. '1,23' o '1.23') a float."""
        if not price_str: return 0.0
        return float(price_str.replace(",", "."))

    def _parse_quantity(self, qty_str: Optional[str]) -> float:
        """Convierte un string de cantidad a float, por defecto 1.0 si es None o vacío."""
        if not qty_str: return 1.0
        return float(qty_str.replace(",", "."))

    def parse_text_to_items(self, raw_text: str) -> Dict[str, Any]:
        """
        Analiza el texto crudo de un ticket y extrae los artículos, subtotal, impuestos y total.
        Devuelve un diccionario con 'items', 'subtotal', 'tax', 'total'.
        """
        lines = raw_text.split('\n')
        parsed_items: List[Item] = []
        extracted_data = {
            "items": [],
            "subtotal": None,
            "tax": None,
            "total": None,
            "raw_text": raw_text
        }
        self.next_item_id = 1 # Reset for each parse

        for line in lines:
            line = line.strip()
            if not line: # Ignorar líneas vacías
                continue

            matched_item = False
            for pattern_name, pattern in self.item_patterns:
                match = pattern.match(line)
                if match:
                    if pattern_name == "qty_unit_name_price":
                        qty_str, name, price_str = match.groups()
                        quantity = self._parse_quantity(qty_str)
                        price = self._parse_price(price_str)
                        name = name.strip()
                        if name and price > 0:
                            parsed_items.append(Item(
                                id=self.next_item_id,
                                name=name,
                                quantity=quantity,
                                price=price,
                                total_price=round(quantity * price, 2)
                            ))
                            self.next_item_id += 1
                            matched_item = True
                            break 
                    elif pattern_name == "name_qty_x_price_totalprice":
                        name, qty_str, price_unit_str, price_total_str = match.groups()
                        quantity = self._parse_quantity(qty_str)
                        price = self._parse_price(price_unit_str) # Usar precio unitario
                        name = name.strip()
                        # Opcional: verificar que qty * price_unit == price_total
                        if name and price > 0:
                             parsed_items.append(Item(
                                id=self.next_item_id,
                                name=name,
                                quantity=quantity,
                                price=price,
                                total_price=round(quantity * price, 2) # o self._parse_price(price_total_str)
                            ))
                             self.next_item_id += 1
                             matched_item = True
                             break
                    elif pattern_name == "total_keywords":
                        keyword, value_str = match.groups()
                        value = self._parse_price(value_str)
                        keyword = keyword.upper()

                        if "TOTAL" in keyword and extracted_data["total"] is None: # Tomar el primer "TOTAL" como el definitivo
                            extracted_data["total"] = value
                        elif "SUBTOTAL" in keyword and extracted_data["subtotal"] is None:
                            extracted_data["subtotal"] = value
                        elif ("IVA" in keyword or "IMPUESTO" in keyword) and extracted_data["tax"] is None:
                            extracted_data["tax"] = value
                        # Podríamos añadir lógica para descuentos, etc.
                        matched_item = True # No es un item, pero la línea fue procesada
                        break
            # Si ninguna regex de item funcionó, podríamos tener una lógica de fallback
            # o registrar la línea como no parseada.
            # if not matched_item:
            # print(f"Línea no parseada: {line}")

        extracted_data["items"] = parsed_items

        # Lógica de post-procesamiento:
        # Si el total no se encontró pero hay items, calcularlo.
        if extracted_data["total"] is None and parsed_items:
            calculated_total = sum(item.total_price for item in parsed_items)
            # Si tenemos subtotal e impuestos, intentar sumarlos si tiene sentido
            if extracted_data["subtotal"] is not None and extracted_data["tax"] is not None:
                if abs(calculated_total - (extracted_data["subtotal"] + extracted_data["tax"])) < 0.05: # Margen pequeño
                    extracted_data["total"] = round(extracted_data["subtotal"] + extracted_data["tax"], 2)
                else: # Si no cuadra, usar la suma de items.
                    extracted_data["total"] = round(calculated_total,2)
            else:
                extracted_data["total"] = round(calculated_total,2)

        # Si el subtotal no se encontró pero sí el total y los impuestos, calcularlo.
        if extracted_data["subtotal"] is None and extracted_data["total"] is not None and extracted_data["tax"] is not None:
            extracted_data["subtotal"] = round(extracted_data["total"] - extracted_data["tax"],2)

        return extracted_data

# Ejemplo de uso:
# if __name__ == '__main__':
#     parser = ParserService()
#     sample_text = """
#     MERCADONA S.A.
#     C/ TAL CUAL
#     -------------------------------------
#     2 KG PLATANO CANARIAS      3.50
#     1 UD LECHE DESNATADA       0.90
#     PAN BARRA                  1.00
#     CERVEZA ESPECIAL VOLL      2 x 1.20      2.40
#     
#     SUBTOTAL: 7.80
#     IVA (10%): 0.78
#     TOTAL: 8.58
#     GRACIAS POR SU VISITA
#     """
#     parsed_data = parser.parse_text_to_items(sample_text)
#     print("Items Parseados:")
#     for item in parsed_data["items"]:
#         print(f"  ID: {item.id}, Nombre: {item.name}, Cant: {item.quantity}, Precio: {item.price}, Total: {item.total_price}")
#     print(f"Subtotal: {parsed_data['subtotal']}")
#     print(f"IVA: {parsed_data['tax']}")
#     print(f"Total: {parsed_data['total']}") 