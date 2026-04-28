import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
BUSINESSES_FILE = os.path.join(DATA_DIR, "businesses.json")
CLIENTS_FILE = os.path.join(DATA_DIR, "clients.json")
INVOICES_FILE = os.path.join(DATA_DIR, "invoices.json")
COMPANY_DETAILS_FILE = os.path.join(DATA_DIR, "company_details.json")

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# --- SINGLE USER COMPATIBILITY (for main.py) ---
def get_company_details():
    return load_json(COMPANY_DETAILS_FILE)

def save_company_details(company):
    save_json(COMPANY_DETAILS_FILE, company)

def load_clients(owner_phone=None):
    all_clients = load_json(CLIENTS_FILE)
    if owner_phone is None:
        # Fallback for main.py: return the first business's clients or empty dict
        # Actually, main.py expects a flat dict of clients
        # Let's check if CLIENTS_FILE is already multi-tenant
        if all_clients and any(isinstance(v, dict) for v in all_clients.values()):
             # It is multi-tenant, return 'default' or first key
             return all_clients.get('default', {})
        return all_clients
    return all_clients.get(owner_phone, {})

def save_clients(clients, owner_phone=None):
    if owner_phone is None:
        # If it's multi-tenant, save to 'default'
        all_clients = load_json(CLIENTS_FILE)
        if all_clients and any(isinstance(v, dict) for v in all_clients.values()):
            all_clients['default'] = clients
            save_json(CLIENTS_FILE, all_clients)
        else:
            save_json(CLIENTS_FILE, clients)
    else:
        all_clients = load_json(CLIENTS_FILE)
        all_clients[owner_phone] = clients
        save_json(CLIENTS_FILE, all_clients)

# --- BUSINESS PROFILES ---
def get_business_profile(owner_phone):
    businesses = load_json(BUSINESSES_FILE)
    return businesses.get(owner_phone)

def save_business_profile(owner_phone, profile):
    businesses = load_json(BUSINESSES_FILE)
    businesses[owner_phone] = profile
    save_json(BUSINESSES_FILE, businesses)

# --- CLIENTS (Scoped per Business) ---
# Note: load_clients and save_clients are now handled above

def save_client(owner_phone, client_data):
    all_clients = load_json(CLIENTS_FILE)
    if owner_phone not in all_clients:
        all_clients[owner_phone] = {}
    
    client_name = client_data.get("name", "Unknown").lower()
    all_clients[owner_phone][client_name] = client_data
    save_json(CLIENTS_FILE, all_clients)

# --- INVOICES (Scoped per Business) ---
def save_invoice_record(owner_phone, invoice_data):
    all_invoices = load_json(INVOICES_FILE)
    if owner_phone not in all_invoices:
        all_invoices[owner_phone] = {}
    
    invoice_id = invoice_data.get("id")
    all_invoices[owner_phone][invoice_id] = invoice_data
    save_json(INVOICES_FILE, all_invoices)

def get_invoice_record(owner_phone, invoice_id):
    all_invoices = load_json(INVOICES_FILE)
    business_invoices = all_invoices.get(owner_phone, {})
    return business_invoices.get(invoice_id)

def mark_invoice_as_paid(owner_phone, invoice_id):
    all_invoices = load_json(INVOICES_FILE)
    if owner_phone in all_invoices and invoice_id in all_invoices[owner_phone]:
        all_invoices[owner_phone][invoice_id]["is_paid"] = True
        save_json(INVOICES_FILE, all_invoices)
        return True
    return False
