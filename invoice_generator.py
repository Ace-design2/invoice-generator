import json
import os
from datetime import datetime
import uuid
import base64

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is not installed.")
    print("Please run: python3 -m pip install playwright && python3 -m playwright install chromium")
    exit(1)

COMPANY_FILE = "company_details.json"

def get_company_details():
    if os.path.exists(COMPANY_FILE):
        with open(COMPANY_FILE, 'r') as f:
            company = json.load(f)
        print(f"Loaded company details for {company.get('name')}.")
        use_existing = input("Do you want to use these details? (y/n) [y]: ").strip().lower()
        if use_existing == 'y' or use_existing == '':
            return company
            
    print("\n--- Enter Company Details ---")
    company = {}
    name_or_logo = input("Company Name or Logo Path (e.g., UNIQUE FOOTWEARS or /path/to/logo.png): ").strip()
    
    if os.path.isfile(name_or_logo):
        company['logo'] = name_or_logo
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
    company['bank2_name'] = input("Bank 2 Name (Optional): ").strip()
    company['bank2_account'] = input("Bank 2 Account Number (Optional): ").strip()
    
    if company.get('logo'):
        company['short_name'] = ""
    else:
        company['short_name'] = input("Company Short Name (e.g., UNIQUE): ").strip()
    
    offers_refund = input("Do you offer refunds? (y/n) [y]: ").strip().lower()
    company['offers_refund'] = (offers_refund == 'y' or offers_refund == '')
    
    if company['offers_refund']:
        default_policy = "Refunds are accepted within 7 days of purchase. Items must be returned in their original packaging, unused, and with the original receipt. Custom or personalized orders are strictly non-refundable. Please allow 3-5 business days for the refund to process to your original payment method. For any issues, contact our support team immediately."
    else:
        default_policy = "All sales are final. We do not accept returns, exchanges, or refunds under any circumstances once a purchase is completed. Please ensure your order is correct before finalizing payment."

    policy = input(f"Enter Policy Text (Press Enter for default, or type 'none' to omit):\n[{default_policy}]\n> ").strip()
    
    if policy.lower() == 'none':
        company['refund_policy_text'] = ""
    else:
        company['refund_policy_text'] = policy if policy else default_policy
    
    with open(COMPANY_FILE, 'w') as f:
        json.dump(company, f, indent=4)
    print("Company details saved!")
    return company

def get_client_details():
    print("\n--- Enter Client Details ---")
    client = {}
    client['name'] = input("Client Name: ").strip()
    client['email'] = input("Client Email: ").strip()
    client['phone'] = input("Client Phone: ").strip()
    client['location'] = input("Client Location: ").strip()
    return client

def get_items():
    print("\n--- Enter Items ---")
    items = []
    while True:
        name = input("Item Name (or press Enter to finish): ").strip()
        if not name:
            break
        try:
            quantity = int(input("Quantity: ").strip())
            price = float(input("Price per item (₦): ").strip())
        except ValueError:
            print("Invalid input for quantity or price. Try again.")
            continue
        items.append({
            'name': name,
            'quantity': quantity,
            'price': price,
            'total': quantity * price
        })
    return items

def get_bank_logo_html(bank_name):
    if not bank_name:
        return ""
    safe_name = bank_name.lower().replace(" ", "")
    for ext in ['.png', '.jpg', '.jpeg', '.svg']:
        path = os.path.join('bank_logos', f'{safe_name}{ext}')
        if os.path.exists(path):
            with open(path, 'rb') as img_file:
                b64_string = base64.b64encode(img_file.read()).decode('utf-8')
            mime = 'image/svg+xml' if ext == '.svg' else f'image/{ext[1:]}'
            return f'<img src="data:{mime};base64,{b64_string}" class="h-4 inline-block mr-1" alt="{bank_name}">'
    return ""

def get_image_base64_html_from_path(path, height_class="h-10"):
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.svg']:
        return ""
    with open(path, 'rb') as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')
    mime = 'image/svg+xml' if ext == '.svg' else f'image/{ext[1:]}'
    return f'<img src="data:{mime};base64,{b64_string}" class="{height_class} object-contain">'

def generate_pdf(company, client, items):
    total_amount = sum(item['total'] for item in items)
    invoice_id = str(uuid.uuid4())[:8].upper()
    date_str = datetime.now().strftime("%B %d, %Y")
    
    items_html = ""
    for item in items:
        items_html += f"""
            <div class="self-stretch px-6 py-2 flex justify-between items-center" style="page-break-inside: avoid; break-inside: avoid;">
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{item['name']}</div>
                <div class="flex justify-start items-start gap-16">
                    <div class="w-12 text-center justify-start text-black text-xs font-bold font-['Inter']">{item['quantity']}</div>
                    <div class="w-32 text-center justify-start text-black text-xs font-bold font-['Inter']">₦{item['price']:,.2f}</div>
                </div>
            </div>"""

    bank1_name = company.get("bank1_name", "")
    bank1_display = f"{get_bank_logo_html(bank1_name)}<span>{bank1_name}</span>" if bank1_name else ""
    
    bank2_name = company.get("bank2_name", "")
    bank2_display = f"{get_bank_logo_html(bank2_name)}<span>{bank2_name}</span>" if bank2_name else ""

    bank2_name_html = f'<div class="w-28 justify-start text-black text-sm font-bold font-[\'Inter\'] flex items-center">{bank2_display}</div>' if bank2_display else ""
    bank2_acc_html = f'<div class="w-28 justify-start text-black text-sm font-normal font-[\'Inter\']">{company.get("bank2_account", "")}</div>' if company.get("bank2_account") else ""

    logo_path = company.get('logo')
    if logo_path and os.path.exists(logo_path):
        top_company_display = get_image_base64_html_from_path(logo_path, "h-12")
        bottom_company_display = get_image_base64_html_from_path(logo_path, "h-12")
    else:
        top_company_display = f"<div class=\"justify-start text-black text-base font-bold font-['Inter']\">{company.get('name', 'COMPANY NAME')}</div>"
        display_short_name = company.get('short_name', company.get('name', 'COMPANY').split()[0] if company.get('name') else 'COMPANY')
        bottom_company_display = f"<div class=\"justify-start text-black text-3xl font-bold font-['Inter']\">{display_short_name}</div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice - {invoice_id}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: white; margin: 0; padding: 0; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        
        /* The container itself */
        .invoice-container {{
            width: 100%;
            min-height: 100vh;
            padding: 0 4rem;
            box-sizing: border-box;
            background-color: white;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            align-items: stretch;
            gap: 1.25rem;
        }}
    </style>
</head>
<body>
<div class="invoice-container">
    <div class="self-stretch px-6 flex flex-col justify-start items-end gap-2.5 pt-12">
        <div class="inline-flex justify-center items-center">
            {top_company_display}
        </div>
    </div>
    <div class="self-stretch px-6 inline-flex justify-start items-center gap-2.5">
        <div class="justify-start text-black text-4xl font-bold font-['Inter']">Invoice</div>
    </div>
    <div class="self-stretch px-6 inline-flex justify-between items-start">
        <div class="inline-flex flex-col justify-center items-start gap-3">
            <div class="justify-start text-black text-xs font-bold font-['Inter']">CUSTOMER DETAILS</div>
            <div class="flex flex-col justify-center items-start gap-1">
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('name', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('email', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('phone', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('location', '')}</div>
            </div>
        </div>
        <div class="inline-flex flex-col justify-center items-end gap-3">
            <div class="justify-start text-black text-xs font-bold font-['Inter']">{company.get('name') or 'COMPANY DETAILS'}</div>
            <div class="flex flex-col justify-center items-end gap-1">
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('contact_name', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('email', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('phone', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('location', '')}</div>
            </div>
        </div>
    </div>
    <div class="self-stretch border-t-[1pt] border-dashed border-black"></div>
    <div class="self-stretch px-6 flex flex-col justify-center items-start gap-1">
        <div class="justify-start text-black text-xs font-bold font-['Inter']">INVOICE ID: {invoice_id}</div>
        <div class="justify-start text-black text-xs font-bold font-['Inter']">DATE: {date_str}</div>
    </div>
    <div class="self-stretch px-6 inline-flex justify-start items-center gap-2.5">
        <div class="flex-1 outline outline-1 outline-offset-[-1px] outline-black inline-flex flex-col justify-start items-start gap-3 pb-3">
            <div class="self-stretch px-6 py-2 outline outline-1 outline-offset-[-1px] outline-black inline-flex justify-between items-center">
                <div class="justify-start text-black text-xs font-bold font-['Inter']">Item(s)</div>
                <div class="flex justify-start items-center gap-16">
                    <div class="w-12 text-center justify-start text-black text-xs font-bold font-['Inter']">Quantity</div>
                    <div class="w-32 text-center justify-start text-black text-xs font-bold font-['Inter']">Price</div>
                </div>
            </div>
            {items_html}
        </div>
    </div>
    <div class="self-stretch px-12 py-2 inline-flex justify-between items-center">
        <div class="justify-start text-black text-xs font-bold font-['Inter']">TOTAL</div>
        <div class="flex justify-start items-start gap-16">
            <div class="w-12 text-center justify-start text-black text-xs font-bold font-['Inter']"></div>
            <div class="w-32 text-center justify-start text-black text-xs font-bold font-['Inter']">₦{total_amount:,.2f}</div>
        </div>
    </div>
    
    <div class="mt-8 self-stretch border-t-[1pt] border-dashed border-black"></div>
    <div class="w-full inline-flex justify-between items-center">
        {bottom_company_display}
        <div class="px-6 inline-flex flex-col justify-center items-start gap-2">
            <div class="w-64 inline-flex justify-between items-center">
                <div class="w-28 justify-start text-black text-sm font-bold font-['Inter'] flex items-center">{bank1_display}</div>
                {bank2_name_html}
            </div>
            <div class="w-64 inline-flex justify-between items-center">
                <div class="w-28 justify-start text-black text-sm font-normal font-['Inter']">{company.get('bank1_account', '')}</div>
                {bank2_acc_html}
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

    refund_policy_text = company.get("refund_policy_text", "")
    footer_policy_html = ""
    if refund_policy_text:
        footer_policy_html = f"""
        <div style="width: 100%; border-top: 1px dashed black; padding-top: 8px; margin-bottom: 8px;">
            <div style="font-weight: bold; font-size: 10px; margin-bottom: 4px;">REFUND POLICY</div>
            <div style="font-size: 10px; font-style: italic; text-align: justify;">{refund_policy_text}</div>
        </div>
        """

    footer_template = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; color: black; padding: 0 64px; width: 100%; box-sizing: border-box;">
        {footer_policy_html}
        <div style="text-align: right; width: 100%; font-size: 10px; font-weight: bold; margin-top: 4px;">
            Page <span class="pageNumber"></span> of <span class="totalPages"></span>
        </div>
    </div>
    """

    filename = f"invoice_{invoice_id}.pdf"
    print("Generating PDF...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        
        # Calculate appropriate bottom margin based on whether there's a refund policy
        bottom_margin = "130px" if refund_policy_text else "40px"
        
        page.pdf(
            path=filename,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer_template,
            margin={"top": "40px", "bottom": bottom_margin, "left": "0px", "right": "0px"}
        )
        
        browser.close()
        
    print(f"\nInvoice successfully generated: {filename}")
    print(f"To open the invoice, run: open {filename}")

def main():
    print("========================================")
    print("        INVOICE GENERATOR CLI")
    print("========================================")
    
    try:
        company = get_company_details()
        
        print("\n--- Quick Invoice (NLP) ---")
        nlp_msg = input("Enter invoice command (e.g., 'Create invoice for John for 50k')\nor press Enter for manual entry: ").strip()
        
        if nlp_msg:
            from nlp_parser import extract_invoice_data
            print("Analyzing message...")
            data = extract_invoice_data(nlp_msg)
            
            client_name = data.get('name') or "Client"
            amount_str = data.get('amount') or "0"
            try:
                amount = float(amount_str)
            except ValueError:
                amount = 0.0
                
            print(f"Extracted -> Name: {client_name}, Amount: ₦{amount:,.2f}")
            
            client = {
                'name': client_name,
                'email': '',
                'phone': '',
                'location': ''
            }
            items = [{
                'name': 'Custom Order',
                'quantity': 1,
                'price': amount,
                'total': amount
            }]
        else:
            client = get_client_details()
            items = get_items()
            
            if not items:
                print("No items added. Exiting.")
                return
            
        generate_pdf(company, client, items)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")

if __name__ == "__main__":
    main()
