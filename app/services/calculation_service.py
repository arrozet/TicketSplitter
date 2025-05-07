from typing import List, Dict, Tuple
from app.models.item import Item
from app.models.receipt import UserShare, ReceiptSplitRequest, ReceiptParseResponse, ReceiptSplitResponse

class CalculationService:

    def calculate_shares(self, parsed_receipt_data: ReceiptParseResponse, split_request: ReceiptSplitRequest) -> ReceiptSplitResponse:
        """
        Calcula la parte correspondiente a cada usuario basándose en los ítems asignados.

        Args:
            parsed_receipt_data: Los datos del ticket ya procesados (incluyendo todos los ítems).
            split_request: La solicitud de división con las asignaciones de ítems a usuarios.

        Returns:
            Un objeto ReceiptSplitResponse con los detalles de la división.
        """
        user_shares: List[UserShare] = []
        # Mapeo de todos los items por ID para fácil acceso
        all_items_map: Dict[int, Item] = {item.id: item for item in parsed_receipt_data.items}
        # Valor total de todos los items en el recibo original
        total_items_value_from_receipt = sum(item.total_price for item in parsed_receipt_data.items)

        # Itera sobre las asignaciones de usuario para crear las participaciones iniciales
        for user_id, item_ids in split_request.user_item_assignments.items():
            user_items: List[Item] = []
            for item_id in item_ids:
                item = all_items_map.get(item_id)
                if item:
                    user_items.append(item)
                else:
                    # Advertencia si un ID de ítem asignado no se encuentra. Podría ser un error del frontend.
                    print(f"Advertencia: Item ID {item_id} asignado a {user_id} no encontrado en el ticket.")
            
            # Se inicializa amount_due en 0.0, se calculará más adelante.
            user_shares.append(UserShare(user_id=user_id, amount_due=0.0, items=user_items))

        num_users = len(split_request.user_item_assignments)
        # Si no hay usuarios y hay items, no se puede dividir. Devuelve respuesta vacía.
        if num_users == 0 and total_items_value_from_receipt > 0:
            return ReceiptSplitResponse(total_calculated=0, shares=[])
        # Si no hay usuarios ni items, división vacía y correcta.
        elif num_users == 0 and total_items_value_from_receipt == 0:
             return ReceiptSplitResponse(total_calculated=0, shares=[])

        # Calcular el valor total de los ítems que fueron asignados directamente a algún usuario.
        current_total_from_direct_assignments = sum(
            item.total_price for share in user_shares for item in share.items
        )

        # Calcular el valor de los ítems que no fueron asignados explícitamente a nadie.
        # Estos se consideran compartidos y se repartirán equitativamente entre todos los usuarios que participan en el split.
        cost_of_unassigned_items = total_items_value_from_receipt - current_total_from_direct_assignments
        share_of_unassigned_items_per_user = (cost_of_unassigned_items / num_users) if num_users > 0 else 0

        # Considerar el total general del recibo (puede incluir impuestos/propinas no itemizados).
        # Si no está explícitamente en parsed_receipt_data.total, se asume que es la suma de los items.
        receipt_total_overall = parsed_receipt_data.total if parsed_receipt_data.total is not None else total_items_value_from_receipt
        
        # Si el total del recibo es mayor que la suma de los items, la diferencia puede ser impuestos/propinas no itemizados.
        # Esta diferencia se reparte equitativamente entre los usuarios.
        # Una lógica más avanzada podría permitir distribuir esto proporcionalmente al gasto de cada uno.
        non_itemized_costs = receipt_total_overall - total_items_value_from_receipt
        share_of_non_itemized_costs_per_user = (non_itemized_costs / num_users) if num_users > 0 and non_itemized_costs > 0 else 0

        final_calculated_total = 0.0
        for share in user_shares:
            # Suma del valor de los items asignados directamente a este usuario
            user_assigned_items_total = sum(item.total_price for item in share.items)
            # La cantidad debida es: sus items + su parte de items no asignados + su parte de costos no itemizados
            amount_due = user_assigned_items_total + share_of_unassigned_items_per_user + share_of_non_itemized_costs_per_user
            share.amount_due = round(amount_due, 2)
            final_calculated_total += share.amount_due
        
        # El total_calculated es la suma de las partes individuales.
        # Podría haber pequeñas discrepancias con parsed_receipt_data.total debido al redondeo
        # o a cómo se distribuyen los costos no itemizados/compartidos.
        return ReceiptSplitResponse(
            total_calculated=round(final_calculated_total, 2),
            shares=user_shares
        )

# Ejemplo (simplificado, no se ejecuta aquí)
# import datetime # Necesario para el ejemplo si se descomenta
# if __name__ == '__main__':
#     calc_service = CalculationService()
#     sample_items = [
#         Item(id=1, name="Pizza", quantity=1, price=15.00, total_price=15.00),
#         Item(id=2, name="CocaCola", quantity=2, price=2.00, total_price=4.00),
#         Item(id=3, name="Agua", quantity=1, price=1.00, total_price=1.00)
#     ]
#     sample_parsed_receipt = ReceiptParseResponse(
#         receipt_id="test1", 
#         upload_timestamp=datetime.datetime.now(),
#         items=sample_items,
#         total=20.00 # Suma de items
#     )
#     sample_split_req = ReceiptSplitRequest(
#         user_item_assignments={
#             "Alice": [1],       # Pizza
#             "Bob": [2,3]      # CocaCola y Agua
#         }
#     )
#     result = calc_service.calculate_shares(sample_parsed_receipt, sample_split_req)
#     # Alice: 15 (Pizza)
#     # Bob: 4 (CocaCola) + 1 (Agua) = 5
#     # Total: 20
#     print(result)

#     sample_split_req_shared = ReceiptSplitRequest(
#         user_item_assignments={
#             "Alice": [2], # CocaCola
#             "Bob": [3]    # Agua
#         } # Pizza (15.00) no asignada
#     )
#     # Pizza (15.00) se divide entre Alice y Bob (7.50 cada uno)
#     # Alice: 2 (CocaCola) + 7.50 = 9.50
#     # Bob: 1 (Agua) + 7.50 = 8.50
#     # Total: 18.00
#     result_shared = calc_service.calculate_shares(sample_parsed_receipt, sample_split_req_shared)
#     print(result_shared) 