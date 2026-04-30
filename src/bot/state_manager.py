class SessionManager:
    def __init__(self):
        # In-memory session store
        self.sessions = {}

    def get_session(self, user_id):
        if user_id not in self.sessions:
            self.sessions[user_id] = self._create_empty_session()
        return self.sessions[user_id]

    def reset_session(self, user_id):
        self.sessions[user_id] = self._create_empty_session()
        return self.sessions[user_id]

    def _create_empty_session(self):
        return {
            "status": "idle", # idle, draft, editing, awaiting_confirmation, confirmed, cancelled
            "invoice": {
                "client": None,
                "items": [],
                "subtotal": 0.0,
                "vat": 0.0,
                "total": 0.0
            },
            "pending_action": None, # e.g., {"type": "send_invoice", "data": ...}
            "context": {
                "last_intent": None
            }
        }

    def update_status(self, user_id, new_status):
        session = self.get_session(user_id)
        
        # Phase 10: Locking After Confirmation
        if session["status"] == "confirmed" and new_status not in ["idle", "draft"]:
            raise Exception("Cannot modify a confirmed invoice.")
            
        session["status"] = new_status
        return session

    def calculate_total(self, invoice):
        """Phase 6: Recalculation Engine"""
        subtotal = sum(item.get("total", 0.0) for item in invoice["items"])
        vat = subtotal * 0.075 # Defaulting to 7.5% VAT for now, or use a field
        
        invoice["subtotal"] = subtotal
        invoice["vat"] = vat
        invoice["total"] = subtotal + vat
        return invoice

    def add_item(self, user_id, item):
        session = self.get_session(user_id)
        
        if session["status"] == "confirmed":
            return False, "This invoice is already confirmed and locked."
            
        # Ensure total is calculated for the new item
        quantity = item.get("quantity", 1)
        price = item.get("price", 0.0)
        item["total"] = quantity * price
        
        session["invoice"]["items"].append(item)
        self.calculate_total(session["invoice"])
        
        if session["status"] in ["idle", "cancelled"]:
            session["status"] = "draft"
        else:
            session["status"] = "editing"
            
        return True, "Item added."

    def update_item(self, user_id, target_name, new_price=None, new_quantity=None):
        session = self.get_session(user_id)
        if session["status"] == "confirmed":
            return False, "This invoice is already confirmed and locked."
            
        found = False
        for item in session["invoice"]["items"]:
            if item["name"].lower() == target_name.lower():
                if new_price is not None:
                    item["price"] = new_price
                if new_quantity is not None:
                    item["quantity"] = new_quantity
                item["total"] = item.get("quantity", 1) * item.get("price", 0.0)
                found = True
                break
                
        if found:
            self.calculate_total(session["invoice"])
            session["status"] = "editing"
            return True, f"Updated {target_name}."
        else:
            return False, f"Item '{target_name}' not found."

    def remove_item(self, user_id, target_name):
        session = self.get_session(user_id)
        if session["status"] == "confirmed":
            return False, "This invoice is already confirmed and locked."
            
        initial_length = len(session["invoice"]["items"])
        session["invoice"]["items"] = [
            item for item in session["invoice"]["items"] 
            if item["name"].lower() != target_name.lower()
        ]
        
        if len(session["invoice"]["items"]) < initial_length:
            self.calculate_total(session["invoice"])
            session["status"] = "editing"
            return True, f"Removed {target_name}."
        else:
            return False, f"Item '{target_name}' not found."

    def set_client(self, user_id, client_data):
        session = self.get_session(user_id)
        if session["status"] == "confirmed":
            return False, "This invoice is already confirmed and locked."
            
        session["invoice"]["client"] = client_data
        if session["status"] in ["idle", "cancelled"]:
            session["status"] = "draft"
        else:
            session["status"] = "editing"
        return True, "Client updated."

    def set_pending_action(self, user_id, action_type, data=None):
        session = self.get_session(user_id)
        session["pending_action"] = {
            "type": action_type,
            "data": data
        }
        session["status"] = "awaiting_confirmation"

    def clear_pending_action(self, user_id):
        session = self.get_session(user_id)
        session["pending_action"] = None
        if session["status"] == "awaiting_confirmation":
            session["status"] = "editing"

# Global instance for the app
session_manager = SessionManager()
