import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
COMPANY_FILE = os.path.join(DATA_DIR, "company_details.json")
CLIENTS_FILE = os.path.join(DATA_DIR, "clients.json")

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

def get_company_details():
    return load_json(COMPANY_FILE)

def save_company_details(company):
    save_json(COMPANY_FILE, company)

def load_clients():
    return load_json(CLIENTS_FILE)

def save_clients(clients):
    save_json(CLIENTS_FILE, clients)
