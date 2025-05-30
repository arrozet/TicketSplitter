from typing import List, Dict, Tuple, Union
from app.models.item import Item
from app.models.receipt import UserShare, ReceiptSplitRequest, ReceiptParseResponse, ReceiptSplitResponse, ItemAssignment

class CalculationService:

    def calculateShares(self, parsed_receipt_data: ReceiptParseResponse, split_request: ReceiptSplitRequest) -> ReceiptSplitResponse:
        """
        Calcula la parte correspondiente a cada usuario basándose en los ítems asignados.
        Ahora soporta asignaciones por cantidad específica y reparte el IVA correctamente.

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
        
        # Diccionario para rastrear cuánta cantidad de cada item ha sido asignada
        assigned_quantities: Dict[int, float] = {}

        # Itera sobre las asignaciones de usuario para crear las participaciones iniciales
        for user_id, assignments in split_request.user_item_assignments.items():
            user_items: List[Item] = []
            user_total_cost = 0.0
            
            # Procesar asignaciones (puede ser lista de IDs o lista de ItemAssignment)
            processed_assignments = self._processUserAssignments(assignments, all_items_map)
            
            for item_id, quantity in processed_assignments:
                original_item = all_items_map.get(item_id)
                if original_item:
                    # Validar que no se exceda la cantidad disponible
                    already_assigned = assigned_quantities.get(item_id, 0.0)
                    if already_assigned + quantity > original_item.quantity:
                        # Ajustar cantidad si excede la disponible
                        available_quantity = original_item.quantity - already_assigned
                        if available_quantity > 0:
                            quantity = available_quantity
                        else:
                            print(f"Advertencia: Item ID {item_id} ya está completamente asignado. Ignorando asignación adicional para {user_id}.")
                            continue
                    
                    # Calcular el costo proporcional
                    proportional_cost = (quantity / original_item.quantity) * original_item.total_price
                    user_total_cost += proportional_cost
                    
                    # Crear un item parcial para este usuario
                    user_item = Item(
                        id=original_item.id,
                        name=original_item.name,
                        quantity=quantity,
                        price=original_item.price,
                        total_price=round(proportional_cost, 2)
                    )
                    user_items.append(user_item)
                    
                    # Actualizar cantidad asignada
                    assigned_quantities[item_id] = assigned_quantities.get(item_id, 0.0) + quantity
                else:
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

        # Calcular elementos compartidos (no asignados) y su costo
        shared_items_info = self._calculateSharedItems(all_items_map, assigned_quantities, num_users)
        cost_of_unassigned_items = shared_items_info['total_cost']
        shared_items_per_user = shared_items_info['items_per_user']
        share_of_unassigned_items_per_user = (cost_of_unassigned_items / num_users) if num_users > 0 else 0

        # --- Lógica de IVA ---
        subtotal = parsed_receipt_data.subtotal if parsed_receipt_data.subtotal is not None else total_items_value_from_receipt
        tax = parsed_receipt_data.tax if parsed_receipt_data.tax is not None else 0.0
        total = parsed_receipt_data.total if parsed_receipt_data.total is not None else subtotal + tax

        # Detectar si el IVA está incluido en los artículos
        # Si subtotal + tax == total (con margen de error pequeño), el IVA NO está incluido
        # Si subtotal ~= total, el IVA ya está incluido
        iva_no_incluido = abs((subtotal + tax) - total) < 0.02 and tax > 0
        iva_incluido = abs(subtotal - total) < 0.02 or tax == 0

        # Calcular el total de artículos asignados a cada usuario (incluyendo compartidos)
        user_totals = []
        for share in user_shares:
            user_total = sum(item.total_price for item in share.items) + share_of_unassigned_items_per_user
            user_totals.append(user_total)

        total_asignado = sum(user_totals)

        # Reparto del IVA solo si NO está incluido
        iva_por_usuario = [0.0 for _ in user_shares]
        if iva_no_incluido and tax > 0 and total_asignado > 0:
            for idx, user_total in enumerate(user_totals):
                iva_por_usuario[idx] = (user_total / total_asignado) * tax
        # Si el IVA ya está incluido, no se reparte nada extra

        final_calculated_total = 0.0
        for idx, share in enumerate(user_shares):
            share.shared_items = shared_items_per_user.copy()
            amount_due = user_totals[idx] + iva_por_usuario[idx]
            share.amount_due = round(amount_due, 2)
            final_calculated_total += share.amount_due
        
        return ReceiptSplitResponse(
            total_calculated=round(final_calculated_total, 2),
            shares=user_shares
        )

    def _processUserAssignments(self, assignments: Union[List[int], List[ItemAssignment]], all_items_map: Dict[int, Item]) -> List[Tuple[int, float]]:
        """
        Procesa las asignaciones de un usuario, normalizándolas a una lista de tuplas (item_id, quantity).
        Mantiene compatibilidad con el formato anterior (lista de IDs) y el nuevo formato (lista de ItemAssignment).
        """
        processed: List[Tuple[int, float]] = []
        
        if not assignments:
            return processed
            
        # Verificar si es el formato nuevo (ItemAssignment) o el anterior (int)
        first_assignment = assignments[0]
        
        if isinstance(first_assignment, dict) or hasattr(first_assignment, 'item_id'):
            # Formato nuevo: ItemAssignment
            for assignment in assignments:
                if isinstance(assignment, dict):
                    item_id = assignment.get('item_id')
                    quantity = assignment.get('quantity', 1.0)
                else:
                    item_id = assignment.item_id
                    quantity = assignment.quantity
                    
                if item_id and quantity > 0:
                    processed.append((item_id, quantity))
        else:
            # Formato anterior: lista de IDs (asigna cantidad completa)
            for item_id in assignments:
                if isinstance(item_id, int) and item_id in all_items_map:
                    original_quantity = all_items_map[item_id].quantity
                    processed.append((item_id, original_quantity))
        
        return processed

    def _calculateSharedItems(self, all_items_map: Dict[int, Item], assigned_quantities: Dict[int, float], num_users: int) -> Dict:
        """
        Calcula los elementos compartidos (no asignados) y crea items proporcionales para cada usuario.
        """
        shared_items_per_user = []
        total_shared_cost = 0.0
        
        for item_id, original_item in all_items_map.items():
            assigned_qty = assigned_quantities.get(item_id, 0.0)
            unassigned_qty = original_item.quantity - assigned_qty
            
            if unassigned_qty > 0:
                # Calcular costo proporcional de la cantidad no asignada
                proportional_cost = (unassigned_qty / original_item.quantity) * original_item.total_price
                total_shared_cost += proportional_cost
                
                # Crear item compartido para cada usuario (cantidad dividida entre todos)
                quantity_per_user = unassigned_qty / num_users if num_users > 0 else 0
                cost_per_user = proportional_cost / num_users if num_users > 0 else 0
                
                shared_item = Item(
                    id=original_item.id,
                    name=original_item.name,
                    quantity=round(quantity_per_user, 3),
                    price=original_item.price,
                    total_price=round(cost_per_user, 2)
                )
                shared_items_per_user.append(shared_item)
        
        return {
            'total_cost': total_shared_cost,
            'items_per_user': shared_items_per_user
        }