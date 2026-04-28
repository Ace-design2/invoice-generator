import os
import uuid
import base64
from datetime import datetime

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is not installed.")
    print("Please run: python3 -m pip install playwright && python3 -m playwright install chromium")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
BANK_LOGOS_DIR = os.path.join(ASSETS_DIR, "bank_logos")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")

def get_bank_logo_html(bank_name):
    if not bank_name:
        return ""
    safe_name = bank_name.lower().replace(" ", "")
    for ext in ['.png', '.jpg', '.jpeg', '.svg']:
        path = os.path.join(BANK_LOGOS_DIR, f'{safe_name}{ext}')
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

def generate_pdf(company, client, items, is_receipt=False, vat_rate=0.0):
    subtotal = sum(item['total'] for item in items)
    vat_amount = subtotal * (vat_rate / 100)
    total_amount = subtotal + vat_amount
    
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

    # --- VAT SECTION ---
    vat_row_html = ""
    if vat_rate > 0:
        vat_row_html = f"""
        <div class="self-stretch px-12 py-1 inline-flex justify-between items-center">
            <div class="justify-start text-black text-[10px] font-normal font-['Inter']">Subtotal</div>
            <div class="w-32 text-center text-black text-[10px] font-normal font-['Inter']">₦{subtotal:,.2f}</div>
        </div>
        <div class="self-stretch px-12 py-1 inline-flex justify-between items-center">
            <div class="justify-start text-black text-[10px] font-normal font-['Inter']">VAT ({vat_rate}%)</div>
            <div class="w-32 text-center text-black text-[10px] font-normal font-['Inter']">₦{vat_amount:,.2f}</div>
        </div>
        """

    bank1_name = company.get("bank1_name", "")
    bank1_display = f"{get_bank_logo_html(bank1_name)}<span>{bank1_name}</span>" if bank1_name else ""
    
    bank2_name = company.get("bank2_name", "")
    bank2_display = f"{get_bank_logo_html(bank2_name)}<span>{bank2_name}</span>" if bank2_name else ""

    bank2_name_html = f'<div class="w-28 justify-start text-black text-sm font-bold font-[\'Inter\'] flex items-center">{bank2_display}</div>' if bank2_display else ""
    bank2_acc_html = f'<div class="w-28 justify-start text-black text-sm font-normal font-[\'Inter\']">{company.get("bank2_account", "")}</div>' if company.get("bank2_account") else ""
    bank2_acc_name_html = f'<div class="w-28 justify-start text-black text-[10px] font-normal font-[\'Inter\']">{company.get("bank2_account_name", "")}</div>' if company.get("bank2_account_name") else ""

    logo_path = company.get('logo')
    if logo_path and os.path.exists(logo_path):
        top_company_display = get_image_base64_html_from_path(logo_path, "h-12")
        bottom_company_display = get_image_base64_html_from_path(logo_path, "h-12")
    else:
        top_company_display = f"<div class=\"justify-start text-black text-base font-bold font-['Inter']\">{company.get('name', 'COMPANY NAME')}</div>"
        display_short_name = company.get('short_name', company.get('name', 'COMPANY').split()[0] if company.get('name') else 'COMPANY')
        bottom_company_display = f"<div class=\"justify-start text-black text-3xl font-bold font-['Inter']\">{display_short_name}</div>"

    document_title = "Receipt" if is_receipt else "Invoice"
    paid_stamp_html = ""
    if is_receipt:
        paid_stamp_html = """
        <div style="position: absolute; top: 150px; right: 50px; transform: rotate(-15deg); border: 6px solid #ef4444; color: #ef4444; font-size: 4rem; font-weight: bold; padding: 0.5rem 1rem; border-radius: 0.5rem; opacity: 0.3; pointer-events: none; z-index: 50; font-family: 'Inter', sans-serif;">
            PAID
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{document_title} - {invoice_id}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: white; margin: 0; padding: 0; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
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
    {paid_stamp_html}
    <div class="self-stretch px-6 flex flex-col justify-start items-end gap-2.5 pt-12">
        <div class="inline-flex justify-center items-center">
            {top_company_display}
        </div>
    </div>
    <div class="self-stretch px-6 inline-flex justify-start items-center gap-2.5">
        <div class="justify-start text-black text-4xl font-bold font-['Inter']">{document_title}</div>
    </div>
    <div class="self-stretch px-6 inline-flex justify-between items-start">
        <div class="inline-flex flex-col justify-center items-start gap-3">
            <div class="justify-start text-black text-xs font-bold font-['Inter']">BILL TO</div>
            <div class="flex flex-col justify-center items-start gap-1">
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('name', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('email', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('phone', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{client.get('location', '')}</div>
            </div>
        </div>
        <div class="inline-flex flex-col justify-center items-end gap-3">
            <div class="justify-start text-black text-xs font-bold font-['Inter']">BILL FROM</div>
            <div class="flex flex-col justify-center items-end gap-1">
                <div class="justify-start text-black text-xs font-bold font-['Inter']">{company.get('name', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('email', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('phone', '')}</div>
                <div class="justify-start text-black text-xs font-normal font-['Inter']">{company.get('location', '')}</div>
            </div>
        </div>
    </div>
    <div class="self-stretch border-t-[1pt] border-dashed border-black"></div>
    <div class="self-stretch px-6 flex flex-col justify-center items-start gap-1">
        <div class="justify-start text-black text-xs font-bold font-['Inter']">{document_title.upper()} ID: {invoice_id}</div>
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
    
    {vat_row_html}
    
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
                <div class="w-28 justify-start text-black text-[10px] font-normal font-['Inter']">{company.get('bank1_account_name', '')}</div>
                {bank2_acc_name_html}
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

    prefix = "receipt" if is_receipt else "invoice"
    filename = f"{prefix}_{invoice_id}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        
        bottom_margin = "130px" if refund_policy_text else "40px"
        
        page.pdf(
            path=file_path,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer_template,
            margin={"top": "40px", "bottom": bottom_margin, "left": "0px", "right": "0px"}
        )
        
        browser.close()
        
    return file_path
