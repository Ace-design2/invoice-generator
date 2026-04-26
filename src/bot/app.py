import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from src.nlp.parser import extract_invoice_data
from src.core.generator import generate_pdf
from src.persistence.storage import get_company_details, load_clients, save_clients
from src.bot.whatsapp_client import send_text_message, upload_media, send_document_message

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Simple session management (In-memory)
# In production, use Redis or a database
user_sessions = {}

@app.route("/webhook", methods=["GET"])
def verify():
    # Meta Webhook verification
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Forbidden", 403
    return "Not Found", 404

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()

    # Check if it's a WhatsApp message
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    from_number = msg.get("from")
                    msg_text = msg.get("text", {}).get("body", "").strip()
                    
                    if msg_text:
                        handle_message(from_number, msg_text)
        
        return "OK", 200
    else:
        return "Not Found", 404

def handle_message(from_number, text):
    session = user_sessions.get(from_number)
    
    # Check if the user wants a receipt for the last sent invoice
    if text.lower() == "receipt" and session and session.get("state") == "INVOICE_SENT":
        send_receipt(from_number)
        return

    # Check if we are waiting for a price input
    if session and session.get("state") == "AWAITING_PRICE":
        process_price_input(from_number, text)
        return

    # Otherwise, treat as a new invoice command
    data = extract_invoice_data(text)
    
    if not data.get("items"):
        send_text_message(from_number, "I couldn't find any items in your message. Try something like '5 bags of rice for Amina'.")
        return

    # Initialize session
    items = []
    for item in data["items"]:
        items.append({
            "name": item["name"],
            "quantity": item["quantity"],
            "price": 0,
            "total": 0
        })
    
    # Try to find client
    client_name = data.get("name")
    client = None
    if client_name:
        clients = load_clients()
        client = clients.get(client_name.lower())
    
    if not client:
        client = {"name": client_name or "Customer", "email": "", "phone": from_number, "location": ""}

    user_sessions[from_number] = {
        "state": "AWAITING_PRICE",
        "items": items,
        "client": client,
        "current_item_index": 0
    }
    
    ask_for_price(from_number)

def ask_for_price(from_number):
    session = user_sessions[from_number]
    idx = session["current_item_index"]
    item = session["items"][idx]
    
    send_text_message(from_number, f"What is the price for {item['name']} (Qty: {item['quantity']})?")

def process_price_input(from_number, text):
    session = user_sessions.get(from_number)
    if not session: return

    try:
        # Clean price input
        clean_text = text.replace("₦", "").replace(",", "").strip()
        price = float(clean_text)
        
        idx = session["current_item_index"]
        session["items"][idx]["price"] = price
        session["items"][idx]["total"] = session["items"][idx]["quantity"] * price
        
        session["current_item_index"] += 1
        
        if session["current_item_index"] < len(session["items"]):
            ask_for_price(from_number)
        else:
            # All prices gathered, generate PDF
            finish_and_send_invoice(from_number)
            
    except ValueError:
        send_text_message(from_number, "Invalid price. Please enter a number (e.g., 5000).")

def finish_and_send_invoice(from_number):
    session = user_sessions.get(from_number)
    if not session: return
    
    send_text_message(from_number, "Generating your invoice... ⏳")
    
    company = get_company_details()
    client = session["client"]
    items = session["items"]
    
    try:
        # Generate Invoice
        pdf_path = generate_pdf(company, client, items)
        
        # Upload to Meta
        upload_res = upload_media(pdf_path)
        media_id = upload_res.get("id")
        
        if media_id:
            send_document_message(from_number, media_id, os.path.basename(pdf_path))
            send_text_message(from_number, "Invoice sent! ✅\nType 'receipt' if you'd like a paid receipt version.")
            
            # Update session to allow receipt generation
            session["state"] = "INVOICE_SENT"
            session["last_invoice_data"] = (company, client, items)
        else:
            send_text_message(from_number, "Failed to upload invoice. Please check logs.")
            print(f"Media upload error: {upload_res}")
            
    except Exception as e:
        send_text_message(from_number, f"An error occurred: {str(e)}")
        print(f"Error generating/sending: {e}")

def send_receipt(from_number):
    session = user_sessions.get(from_number)
    if not session or "last_invoice_data" not in session:
        send_text_message(from_number, "No recent invoice found to generate a receipt for.")
        return
        
    company, client, items = session["last_invoice_data"]
    
    send_text_message(from_number, "Generating your receipt... 🧾")
    
    try:
        receipt_path = generate_pdf(company, client, items, is_receipt=True)
        upload_res = upload_media(receipt_path)
        media_id = upload_res.get("id")
        
        if media_id:
            send_document_message(from_number, media_id, os.path.basename(receipt_path))
            # Keep state as INVOICE_SENT or reset? Let's reset for now or keep for multiple receipts if needed.
        else:
            send_text_message(from_number, "Failed to upload receipt.")
    except Exception as e:
        send_text_message(from_number, f"Error: {str(e)}")
        print(f"Error generating/sending receipt: {e}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
