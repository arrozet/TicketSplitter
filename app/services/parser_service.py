import re
import json # Para parsear la respuesta JSON de Gemini
from typing import List, Dict, Any, Optional
from app.models.item import Item, ItemCreate # Asumiendo que ItemCreate y Item están definidos

class ParserService:
    def __init__(self):
        # Las regex para extraer totales podrían seguir siendo útiles como fallback 
        # o si Gemini no los proporciona de forma consistente en el JSON principal.
        # Por ahora, las mantenemos por si son necesarias para complementar el JSON.
        self.total_patterns = [
            re.compile(r"^(TOTAL\s*(?:NETO|BRUTO|A PAGAR)?):?\s*€?(\d+[,.]\d{1,2})\s*€?$", re.IGNORECASE),
            re.compile(r"^(SUBTOTAL|BASE IMPONIBLE):?\s*€?(\d+[,.]\d{1,2})\s*€?$", re.IGNORECASE),
            re.compile(r"^(?:IVA|VAT|IMPUESTOS)\s*(?:\(\s*\d{1,2}\s*%\s*\))?:?\s*€?(\d+[,.]\d{1,2})\s*€?$", re.IGNORECASE),
        ]
        self.next_item_id = 1

    def _parse_price(self, price_val: Any) -> Optional[float]:
        if price_val is None: return None
        try:
            if isinstance(price_val, (int, float)):
                return float(price_val)
            if isinstance(price_val, str):
                return float(price_val.replace(",", "."))
        except ValueError:
            return None
        return None

    def _parse_quantity(self, qty_val: Any) -> float:
        if qty_val is None: return 1.0 # Default quantity
        try:
            if isinstance(qty_val, (int, float)):
                return float(qty_val)
            if isinstance(qty_val, str):
                val = float(qty_val.replace(",", "."))
                return val if val > 0 else 1.0
        except ValueError:
            return 1.0
        return 1.0

    def parse_text_to_items(self, raw_text_json: str) -> Dict[str, Any]:
        """
        Analiza el texto (que se espera sea JSON) de un ticket y extrae los artículos y totales.
        """
        parsed_items: List[Item] = []
        extracted_data = {
            "items": [],
            "subtotal": None,
            "tax": None,
            "total": None,
            "raw_text": raw_text_json, # Guardamos el JSON original por si acaso
            "is_ticket": True,  # Por defecto asumimos que es un ticket
            "error_message": None,
            "detected_content": None
        }
        self.next_item_id = 1

        try:
            # Intentar parsear el texto de entrada como JSON
            data_from_gemini = json.loads(raw_text_json)
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON de Gemini: {e}. Raw text: {raw_text_json[:500]}...")
            # Si falla el parseo de JSON, podríamos intentar un fallback a regex sobre el texto original,
            # pero por ahora simplemente devolveremos los datos vacíos y un error.
            # Opcional: Podríamos re-lanzar un error aquí o manejarlo de otra forma.
            # raise ValueError(f"El texto de OCR no es un JSON válido: {e}") from e
            return extracted_data # Devuelve datos vacíos si el JSON es inválido

        # Verificar si la imagen es un ticket válido
        is_ticket = data_from_gemini.get("is_ticket", True)
        extracted_data["is_ticket"] = is_ticket
        
        if not is_ticket:
            # Si no es un ticket, devolver el mensaje de error
            extracted_data["error_message"] = data_from_gemini.get("error_message", "La imagen no parece ser un ticket válido.")
            extracted_data["detected_content"] = data_from_gemini.get("detected_content")
            return extracted_data

        gemini_items = data_from_gemini.get("items", [])
        for g_item in gemini_items:
            desc = g_item.get("description")
            qty = self._parse_quantity(g_item.get("quantity"))
            unit_price = self._parse_price(g_item.get("unit_price"))

            if desc and unit_price is not None: # unit_price puede ser 0.0
                parsed_items.append(Item(
                    id=self.next_item_id,
                    name=str(desc).strip(),
                    quantity=qty,
                    price=unit_price,
                    total_price=round(qty * unit_price, 2)
                ))
                self.next_item_id += 1
        
        extracted_data["items"] = parsed_items
        extracted_data["subtotal"] = self._parse_price(data_from_gemini.get("subtotal"))
        extracted_data["tax"] = self._parse_price(data_from_gemini.get("tax"))
        extracted_data["total"] = self._parse_price(data_from_gemini.get("total"))

        # Lógica de post-procesamiento (similar a la anterior, puede ser útil si faltan datos del JSON)
        if not parsed_items and extracted_data["total"] is None:
             print("No se encontraron ítems ni total en el JSON de Gemini.")

        if extracted_data["total"] is None and parsed_items:
            calculated_total = sum(item.total_price for item in parsed_items)
            if extracted_data["subtotal"] is not None and extracted_data["tax"] is not None:
                if abs(calculated_total - (extracted_data["subtotal"] + extracted_data["tax"])) < 0.05:
                    extracted_data["total"] = round(extracted_data["subtotal"] + extracted_data["tax"], 2)
                else:
                    extracted_data["total"] = round(calculated_total, 2)
            else:
                extracted_data["total"] = round(calculated_total, 2)

        if extracted_data["subtotal"] is None and extracted_data["total"] is not None and extracted_data["tax"] is not None:
            extracted_data["subtotal"] = round(extracted_data["total"] - extracted_data["tax"], 2)
        elif extracted_data["subtotal"] is None and parsed_items and extracted_data["total"] is not None and extracted_data["tax"] is None:
            # Si tenemos items y total, pero no subtotal ni impuestos, podemos asumir que el subtotal es la suma de items.
            # Esto es una heurística y puede no ser siempre correcta.
            calculated_subtotal_from_items = sum(item.total_price for item in parsed_items)
            extracted_data["subtotal"] = round(calculated_subtotal_from_items, 2)

        return extracted_data

# Ejemplo de uso (actualizado para esperar JSON):
# if __name__ == '__main__':
#     parser = ParserService()
#     sample_json_text = """ 
# {\n#   \"items\": [\n#     {\"description\": \"Agua Grande\", \"quantity\": 1, \"unit_price\": 1.30},\n#     {\"description\": \"Caña Cerveza\", \"quantity\": 6, \"unit_price\": 1.30}\n#   ],\n#   \"subtotal\": 9.10,\n#   \"tax\": 0.91,\n#   \"total\": 10.01\n# }\n# """
#     parsed_data = parser.parse_text_to_items(sample_json_text)
#     print("Items Parseados:")
#     if parsed_data["items"]:
#         for item in parsed_data["items"]:
#             print(f"  ID: {item.id}, Nombre: {item.name}, Cant: {item.quantity}, Precio: {item.price}, Total: {item.total_price}")
#     else:
#         print("  No se parsearon items.")
#     print(f"Subtotal: {parsed_data['subtotal']}")
#     print(f"IVA: {parsed_data['tax']}")
#     print(f"Total: {parsed_data['total']}") 