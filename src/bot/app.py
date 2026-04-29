import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from src.nlp.parser import extract_invoice_data, extract_invoice_data_multimodal
from src.core.generator import generate_pdf
from src.persistence.storage import (
    get_business_profile, save_business_profile, 
    load_clients, save_client,
    save_invoice_record, get_invoice_record, mark_invoice_as_paid
)
from src.bot.whatsapp_client import (
    send_text_message, upload_media, send_document_message,
    get_media_url, download_media
)

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Simple session management (In-memory)
user_sessions = {}

@app.route("/privacy")
def privacy():
    return """<html><body style='font-family:sans-serif;padding:40px;'><h1>Privacy Policy</h1><p>We only process data to generate invoices.</p></body></html>""", 200

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    from_number = msg.get("from")
                    msg_type = msg.get("type")
                    
                    if msg_type == "text":
                        msg_text = msg.get("text", {}).get("body", "").strip()
                        if msg_text:
                            handle_message(from_number, msg_text)
                    elif msg_type == "image":
                        handle_media_message(from_number, msg.get("image", {}), "image")
                    elif msg_type in ["audio", "voice"]:
                        handle_media_message(from_number, msg.get("audio", {}), "audio")
        return "OK", 200
    return "Not Found", 404

def handle_media_message(from_number, media_obj, media_type):
    media_id = media_obj.get("id")
    mime_type = media_obj.get("mime_type")
    
    send_text_message(from_number, f"Got your {media_type}! Processing... ⏳")
    
    # 1. Get URL
    media_url = get_media_url(media_id)
    if not media_url:
        send_text_message(from_number, "Failed to retrieve media. Please try again.")
        return

    # 2. Download
    ext = mime_type.split("/")[-1].split(";")[0]
    # Handle some common mime types
    if "ogg" in ext: ext = "ogg"
    elif "jpeg" in ext: ext = "jpg"
    
    temp_path = f"assets/temp_media/{media_id}.{ext}"
    download_media(media_url, temp_path)
    
    # 3. Parse with Gemini
    try:
        data = extract_invoice_data_multimodal(temp_path, mime_type)
        
        # 4. Process like a text message (update session)
        process_parsed_data(from_number, data)
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Error processing multimodal: {e}")
        send_text_message(from_number, "Sorry, I couldn't understand that media. Could you try typing the details?")

def process_parsed_data(from_number, data):
    session = user_sessions.get(from_number)
    if not session or session.get("state") == "INVOICE_SENT":
        session = {"state": "COLLECTING_DATA", "items": [], "client": None}
        user_sessions[from_number] = session

    # Update Client
    if data.get("name") and not session.get("client"):
        clients = load_clients(from_number)
        client = clients.get(data["name"].lower())
        if not client:
            client = {"name": data["name"], "email": "", "phone": "", "location": ""}
            save_client(from_number, client)
        session["client"] = client

    # Update Items
    if data.get("items"):
        session["items"].extend(data["items"])

    check_draft_completeness(from_number)

def handle_message(from_number, text):
    session = user_sessions.get(from_number)
    text_lower = text.lower()
    
    # 1. AUTH & PROFILE CHECK
    profile = get_business_profile(from_number)
    if not profile and text_lower not in ["start", "invoice", "hi", "hello"]:
        # Check if they are in the middle of any business setup state
        is_setup_state = session and ("BIZ" in session.get("state", "") or "REFUND" in session.get("state", ""))
        if is_setup_state:
            pass 
        else:
            send_text_message(from_number, "Welcome! Please set up your business profile first.\n\nType 'start' to begin.")
            return

    # 2. GLOBAL TRIGGERS
    if text_lower in ["start", "hi", "hello", "new", "reset"]:
        if not profile:
            start_business_setup(from_number)
        else:
            user_sessions[from_number] = {"state": "COLLECTING_DATA", "items": [], "client": None}
            send_text_message(from_number, "Let's create an invoice! 📝\n\nWho is the client, and what are you selling? (e.g., '2 laptops for Segun at 300k')")
        return

    if text_lower == "receipt" and session and session.get("state") == "INVOICE_SENT":
        send_receipt(from_number)
        return

    # 3. STATE MACHINE
    if session:
        state = session.get("state")
        
        # --- Profile Setup ---
        if state == "AWAITING_BIZ_NAME": process_biz_name(from_number, text); return
        if state == "AWAITING_BIZ_EMAIL": process_biz_email(from_number, text); return
        if state == "AWAITING_BIZ_BANK1": process_biz_bank1(from_number, text); return
        if state == "AWAITING_BIZ_BANK2": process_biz_bank2(from_number, text); return
        if state == "AWAITING_REFUND_POLICY": process_refund_policy(from_number, text); return

        # --- Conversational Invoice Flow ---
        if state == "AWAITING_CLIENT_NAME": process_client_name(from_number, text); return
        if state == "AWAITING_ITEM_PRICE": process_item_price(from_number, text); return
        if state == "AWAITING_CONFIRMATION":
            if text_lower in ["yes", "y", "confirm", "ok", "send"]:
                session["state"] = "AWAITING_VAT_CHOICE"
                send_text_message(from_number, "Add 7.5% VAT? (Yes/No)")
            elif text_lower in ["no", "edit", "change"]:
                send_text_message(from_number, "What would you like to change? (e.g., 'Price is 50k' or 'Client is John')")
            else:
                # Treat as an edit
                process_data_input(from_number, text)
            return

        if state == "AWAITING_VAT_CHOICE":
            session["vat_rate"] = 7.5 if text_lower in ["yes", "y"] else 0.0
            finish_and_send_invoice(from_number)
            return

    # Default: Process as data input
    process_data_input(from_number, text)

def process_data_input(from_number, text):
    session = user_sessions.get(from_number)
    if not session or session.get("state") == "INVOICE_SENT":
        session = {"state": "COLLECTING_DATA", "items": [], "client": None}
        user_sessions[from_number] = session

    # Parse the input
    data = extract_invoice_data(text)
    
    # Update Client if found (and not already set)
    if data.get("name") and not session.get("client"):
        clients = load_clients(from_number)
        client = clients.get(data["name"].lower())
        if not client:
            client = {"name": data["name"], "email": "", "phone": "", "location": ""}
            save_client(from_number, client)
        session["client"] = client

    # Update Items if found
    if data.get("items"):
        session["items"].extend(data["items"])

    # If user sent just a number and we are missing a price
    if not data.get("items") and session["items"]:
        try:
            clean_text = text.replace("₦", "").replace(",", "").strip()
            # Handle "10k" or "500"
            if clean_text.lower().endswith('k'):
                price = float(clean_text[:-1]) * 1000
            else:
                price = float(clean_text)
            
            # Find the first item that is missing a price and update it
            for item in session["items"]:
                if item["price"] == 0:
                    item["price"] = price
                    item["total"] = item["quantity"] * price
                    break
        except ValueError:
            pass

    # CHECK COMPLETENESS
    check_draft_completeness(from_number)

def process_client_name(from_number, text):
    session = user_sessions.get(from_number)
    if not session: return
    
    # Simple logic: the whole text is the name
    client = {"name": text.strip(), "email": "", "phone": "", "location": ""}
    save_client(from_number, client)
    session["client"] = client
    session["state"] = "COLLECTING_DATA"
    
    check_draft_completeness(from_number)

def process_item_price(from_number, text):
    session = user_sessions.get(from_number)
    if not session: return

    try:
        clean_text = text.replace("₦", "").replace(",", "").strip()
        if clean_text.lower().endswith('k'):
            price = float(clean_text[:-1]) * 1000
        else:
            price = float(clean_text)
        
        # Find the first item that is missing a price and update it
        for item in session["items"]:
            if item["price"] == 0:
                item["price"] = price
                item["total"] = item["quantity"] * price
                break
        
        session["state"] = "COLLECTING_DATA"
    except ValueError:
        send_text_message(from_number, "I didn't catch that price. Please enter a number (e.g. 5000 or 5k).")
        return

    check_draft_completeness(from_number)

def check_draft_completeness(from_number):
    session = user_sessions[from_number]
    
    if not session["client"]:
        session["state"] = "AWAITING_CLIENT_NAME"
        send_text_message(from_number, "Who is the client for this invoice?")
        return

    if not session["items"]:
        client_name = session["client"]["name"]
        send_text_message(from_number, f"Got the client: *{client_name}*. ✅\n\nNow, what are you selling and at what price?\n(Example: 'Rice 2000' or '2 Laptops at 300k each')")
        return

    # Check for items without prices
    for item in session["items"]:
        if item["price"] == 0:
            session["state"] = "AWAITING_ITEM_PRICE"
            send_text_message(from_number, f"What is the price for {item['name']}?")
            return

    # EVERYTHING FOUND -> SHOW PREVIEW
    show_confirmation_preview(from_number)

def show_confirmation_preview(from_number):
    session = user_sessions[from_number]
    session["state"] = "AWAITING_CONFIRMATION"
    
    items_text = ""
    subtotal = 0
    for item in session["items"]:
        items_text += f"• {item['quantity']} {item['name']} @ ₦{item['price']:,.0f}\n"
        subtotal += item['total']
    
    preview = (
        f"📝 *Invoice Preview*\n\n"
        f"👤 *Client:* {session['client']['name']}\n"
        f"📦 *Items:*\n{items_text}\n"
        f"💰 *Total:* ₦{subtotal:,.0f}\n\n"
        f"Confirm? (Yes/Edit)"
    )
    send_text_message(from_number, preview)

# --- BUSINESS SETUP (Keep original logic) ---
def start_business_setup(from_number):
    user_sessions[from_number] = {"state": "AWAITING_BIZ_NAME"}
    send_text_message(from_number, "Business Setup: What is your Business Name?")

def process_biz_name(from_number, text):
    user_sessions[from_number] = {"state": "AWAITING_BIZ_EMAIL", "biz_name": text}
    send_text_message(from_number, "Business Email?")

def process_biz_email(from_number, text):
    user_sessions[from_number].update({"biz_email": text, "state": "AWAITING_BIZ_BANK1"})
    send_text_message(from_number, "Bank details? (Bank, Acc Number, Acc Name)")

def process_biz_bank1(from_number, text):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        send_text_message(from_number, "Provide Bank, Acc Number, Acc Name.")
        return
    user_sessions[from_number].update({"bank1": parts, "state": "AWAITING_BIZ_BANK2"})
    send_text_message(from_number, "Second bank? (or 'none')")

def process_biz_bank2(from_number, text):
    if text.lower() != "none":
        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 3: user_sessions[from_number]["bank2"] = parts
    user_sessions[from_number]["state"] = "AWAITING_REFUND_POLICY"
    send_text_message(from_number, "Finally, let's set your Refund Policy. 📜\n\nType 'default' to use our standard policy, 'none' for no policy, or type out your custom policy.")

def process_refund_policy(from_number, text):
    session = user_sessions[from_number]
    
    # Professional Default Policy
    DEFAULT_POLICY = (
        "Thank you for your business. Please note that all sales are final. "
        "Refunds or exchanges are only permitted within 7 days of purchase for items found to be defective. "
        "Items must be returned in their original packaging with the invoice."
    )
    
    if text.lower() == "default":
        refund_text = DEFAULT_POLICY
    elif text.lower() == "none":
        refund_text = ""
    else:
        refund_text = text
        
    bank1 = session["bank1"]
    bank2 = session.get("bank2", [None, None, None])
    profile = {
        "name": session["biz_name"], "email": session["biz_email"], "phone": from_number,
        "bank1_name": bank1[0], "bank1_account": bank1[1], "bank1_account_name": bank1[2],
        "bank2_name": bank2[0], "bank2_account": bank2[1], "bank2_account_name": bank2[2],
        "refund_policy_text": refund_text, "location": "Lagos"
    }
    save_business_profile(from_number, profile)
    send_text_message(from_number, "Profile saved! ✅ Type 'invoice' to start.")
    del user_sessions[from_number]

def finish_and_send_invoice(from_number):
    session = user_sessions.get(from_number)
    send_text_message(from_number, "Generating your invoice... ⏳")
    profile = get_business_profile(from_number)
    vat_rate = session.get("vat_rate", 0.0)
    pdf_path = generate_pdf(profile, session["client"], session["items"], vat_rate=vat_rate)
    invoice_id = os.path.basename(pdf_path).split("_")[1].replace(".pdf", "")
    save_invoice_record(from_number, {
        "id": invoice_id, "client": session["client"], "items": session["items"],
        "vat_rate": vat_rate, "total": sum(i["total"] for i in session["items"]) * (1 + vat_rate/100),
        "is_paid": False, "timestamp": str(datetime.now())
    })
    media_id = upload_media(pdf_path).get("id")
    if media_id:
        send_document_message(from_number, media_id, os.path.basename(pdf_path))
        send_text_message(from_number, f"Invoice {invoice_id} sent! ✅ Type 'receipt' if paid.")
        session["state"] = "INVOICE_SENT"; session["last_invoice_id"] = invoice_id
    else:
        send_text_message(from_number, "Failed to upload.")

def send_receipt(from_number):
    session = user_sessions.get(from_number)
    inv_id = session.get("last_invoice_id")
    record = get_invoice_record(from_number, inv_id)
    mark_invoice_as_paid(from_number, inv_id)
    profile = get_business_profile(from_number)
    path = generate_pdf(profile, record["client"], record["items"], is_receipt=True, vat_rate=record.get("vat_rate", 0.0))
    media_id = upload_media(path).get("id")
    if media_id: send_document_message(from_number, media_id, os.path.basename(path))

if __name__ == "__main__":
    app.run(port=5001, debug=True)
