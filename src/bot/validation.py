def validate_add_item(entities):
    """
    Phase 3: Input Validation
    Check for missing or invalid data when adding an item.
    """
    items = entities.get("items", [])
    if not items:
        return False, "Item details are missing."
        
    for item in items:
        if not item.get("name"):
            return False, "Item name is missing."
        if item.get("price") is None or item.get("price") < 0:
            return False, f"Price for '{item.get('name')}' is missing or invalid."
        if item.get("quantity") is None or item.get("quantity") <= 0:
            return False, f"Quantity for '{item.get('name')}' is invalid."
            
    return True, ""

def validate_update_item(entities):
    if not entities.get("target_item_name"):
        return False, "Please specify which item you want to update."
    
    new_price = entities.get("new_price")
    new_qty = entities.get("new_quantity")
    
    if new_price is None and new_qty is None:
        return False, "Please specify the new price or quantity."
        
    return True, ""

def validate_remove_item(entities):
    if not entities.get("target_item_name"):
        return False, "Please specify which item you want to remove."
    return True, ""

def validate_invoice_for_sending(invoice):
    """
    Phase 3: Business Logic Validation
    Before sending, check if the invoice is valid.
    """
    if not invoice.get("client") or not invoice["client"].get("name"):
        return False, "Invoice must have a client name before sending."
        
    if not invoice.get("items") or len(invoice["items"]) == 0:
        return False, "Invoice must have at least one item before sending."
        
    if invoice.get("total", 0) <= 0:
        return False, "Invoice total must be greater than 0."
        
    return True, ""

def check_confidence(confidence, threshold=0.7):
    """
    Phase 3: NLP Confidence Handling
    """
    if confidence is None:
        return False
    return confidence >= threshold
