import os
import sys
from src.persistence.storage import get_company_details, save_company_details, load_clients, save_clients
from src.core.generator import generate_pdf
from src.nlp.parser import extract_invoice_data

def setup_company():
    company = get_company_details()
    if company:
        print(f"Loaded company details for {company.get('name')}.")
        use_existing = input("Do you want to use these details? (y/n) [y]: ").strip().lower()
        if use_existing == 'y' or use_existing == '':
            return company
            
    print("\n--- Enter Company Details ---")
    company = {}
    name_or_logo = input("Company Name or Logo Path (e.g., UNIQUE FOOTWEARS or /path/to/logo.png): ").strip()
    
    if os.path.isfile(name_or_logo):
        company['logo'] = os.path.abspath(name_or_logo)
        company['name'] = ""
    else:
        company['logo'] = ""
        company['name'] = name_or_logo
        
    company['contact_name'] = input("Contact Name: ").strip()
    company['email'] = input("Email: ").strip()
    company['phone'] = input("Phone Number: ").strip()
    company['location'] = input("Location: ").strip()
    company['bank1_name'] = input("Bank 1 Name: ").strip()
    company['bank1_account'] = input("Bank 1 Account Number: ").strip()
    company['bank1_account_name'] = input("Bank 1 Account Name: ").strip()
    company['bank2_name'] = input("Bank 2 Name (Optional): ").strip()
    company['bank2_account'] = input("Bank 2 Account Number (Optional): ").strip()
    company['bank2_account_name'] = input("Bank 2 Account Name (Optional): ").strip()
    
    if not company.get('logo'):
        company['short_name'] = input("Company Short Name (e.g., UNIQUE): ").strip()
    else:
        company['short_name'] = ""
    
    offers_refund = input("Do you offer refunds? (y/n) [y]: ").strip().lower()
    company['offers_refund'] = (offers_refund == 'y' or offers_refund == '')
    
    if company['offers_refund']:
        default_policy = "Refunds are accepted within 7 days of purchase. Items must be returned in their original packaging, unused, and with the original receipt."
    else:
        default_policy = "All sales are final. We do not accept returns, exchanges, or refunds."

    policy = input(f"Enter Policy Text (Press Enter for default):\n[{default_policy}]\n> ").strip()
    company['refund_policy_text'] = policy if policy else default_policy
    
    save_company_details(company)
    print("Company details saved!")
    return company

def get_or_create_client(name_hint=None):
    clients = load_clients()
    client_name = name_hint
    
    if not client_name:
        print("\n--- Enter Client Details ---")
        client_name = input("Client Name: ").strip()
        while not client_name:
            client_name = input("Client Name cannot be empty. Client Name: ").strip()
            
    client_key = client_name.lower()
    
    if client_key in clients:
        use_existing = input(f"Found saved details for '{clients[client_key]['name']}'. Use them? (y/n) [y]: ").strip().lower()
        if use_existing == 'y' or use_existing == '':
            return clients[client_key]
            
    print(f"\nEntering details for {client_name}:")
    client = {
        'name': client_name,
        'email': input("Client Email (optional): ").strip(),
        'phone': input("Client Phone (optional): ").strip(),
        'location': input("Client Location (optional): ").strip()
    }
    
    clients[client_key] = client
    save_clients(clients)
    return client

def get_items_manually():
    print("\n--- Enter Items ---")
    items = []
    while True:
        name = input("Item Name (or press Enter to finish): ").strip()
        if not name:
            break
        try:
            quantity = int(input("Quantity: ").strip())
            price = float(input("Price per item (₦): ").strip())
            items.append({
                'name': name,
                'quantity': quantity,
                'price': price,
                'total': quantity * price
            })
        except ValueError:
            print("Invalid input. Try again.")
    return items

def main():
    print("========================================")
    print("      INVOICE GENERATOR - ACTUAL APP")
    print("========================================")
    
    try:
        company = setup_company()
        
        print("\n--- Create Invoice ---")
        msg = input("Enter invoice command (NLP) or press Enter for manual: ").strip()
        
        if msg:
            data = extract_invoice_data(msg)
            client_name = data.get('name') or input("Client Name: ").strip()
            client = get_or_create_client(client_name)
            
            items = []
            if data.get('items'):
                for ext_item in data['items']:
                    if ext_item.get('price') and ext_item['price'] > 0:
                        price = ext_item['price']
                        print(f"Using parsed price for {ext_item['name']}: ₦{price:,.2f}")
                    else:
                        price_input = input(f"Price for {ext_item['name']} (Qty: {ext_item['quantity']}): ₦").strip()
                        try:
                            price = float(price_input)
                        except ValueError:
                            price = 0
                    
                    if price > 0:
                        items.append({
                            'name': ext_item['name'],
                            'quantity': ext_item['quantity'],
                            'price': price,
                            'total': ext_item['quantity'] * price
                        })
            elif data.get('amount'):
                items = [{
                    'name': 'Custom Order',
                    'quantity': 1,
                    'price': float(data['amount']),
                    'total': float(data['amount'])
                }]
            
            if not items:
                items = get_items_manually()
        else:
            client = get_or_create_client()
            items = get_items_manually()
            
        if items:
            file_path = generate_pdf(company, client, items)
            print(f"\nInvoice generated: {file_path}")
            print(f"To open: open \"{file_path}\"")
            
            gen_receipt = input("\nDo you want to generate a receipt for this? (y/n) [n]: ").strip().lower()
            if gen_receipt == 'y':
                receipt_path = generate_pdf(company, client, items, is_receipt=True)
                print(f"Receipt generated: {receipt_path}")
                print(f"To open: open \"{receipt_path}\"")
        else:
            print("No items, no invoice.")
            
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
