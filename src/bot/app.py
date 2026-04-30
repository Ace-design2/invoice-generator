import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from src.nlp.parser import extract_intent, extract_intent_multimodal
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
from src.bot.state_manager import session_manager
from src.bot.validation import (
    validate_add_item, validate_update_item, validate_remove_item,
    validate_invoice_for_sending, check_confidence
)

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

@app.route("/privacy")
def privacy():
    return "<html><body style='font-family:sans-serif;padding:40px;'><h1>Privacy Policy</h1><p>We only process data to generate invoices.</p></body></html>", 200

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
    
    media_url = get_media_url(media_id)
    if not media_url:
        send_text_message(from_number, "Failed to retrieve media. Please try again.")
        return

    ext = mime_type.split("/")[-1].split(";")[0]
    if "ogg" in ext: ext = "ogg"
    elif "jpeg" in ext: ext = "jpg"
    
    os.makedirs("assets/temp_media", exist_ok=True)
    temp_path = f"assets/temp_media/{media_id}.{ext}"
    download_media(media_url, temp_path)
    
    try:
        data = extract_intent_multimodal(temp_path, mime_type)
        process_intent(from_number, data, original_text=f"[{media_type} message]")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Error processing multimodal: {e}")
        send_text_message(from_number, "Sorry, I couldn't understand that media. Could you try typing the details?")

def handle_message(from_number, text):
    text_lower = text.lower()
    
    profile = get_business_profile(from_number)
    
    # We use a secondary lightweight session just for the business setup phase, 
    # since session_manager is optimized for the invoice flow.
    # To keep it clean, we'll store setup state in memory locally.
    global setup_sessions
    if 'setup_sessions' not in globals():
        setup_sessions = {}
        
    setup_state = setup_sessions.get(from_number, {}).get("state", "")
    
    if not profile and text_lower not in ["start", "invoice", "hi", "hello"]:
        if "AWAITING" in setup_state:
            pass # allow setup to continue
        else:
            send_text_message(from_number, "Welcome! Please set up your business profile first.\n\nType 'start' to begin.")
            return

    if text_lower in ["start", "hi", "hello", "new", "reset"]:
        if not profile:
            start_business_setup(from_number)
        else:
            biz_name = profile.get("name", "")
            send_text_message(from_number, f"Hello {biz_name}! 👋 Welcome back. To create an invoice, just tell me what you're selling. (e.g., '2 laptops for John at 300k')")
        return

    # Check if in setup mode
    if "AWAITING" in setup_state:
        if setup_state == "AWAITING_BIZ_NAME": process_biz_name(from_number, text); return
        if setup_state == "AWAITING_BIZ_EMAIL": process_biz_email(from_number, text); return
        if setup_state == "AWAITING_BIZ_BANK1": process_biz_bank1(from_number, text); return
        if setup_state == "AWAITING_BIZ_BANK2": process_biz_bank2(from_number, text); return
        if setup_state == "AWAITING_REFUND_POLICY": process_refund_policy(from_number, text); return

    if text_lower == "receipt":
        send_receipt(from_number)
        return

    # 1. NLP Intent Extraction
    if text_lower in ["send it", "send"]:
        data = {"intent": "send_invoice", "confidence": 1.0, "entities": {}}
    else:
        data = extract_intent(text)
    
    # 2. Logging & Debugging (Phase 11)
    print(f"--- LOG ---")
    print(f"USER: {text}")
    print(f"INTENT: {json.dumps(data, indent=2)}")
    print(f"-----------")

    # 3. Process Intent
    process_intent(from_number, data, original_text=text)

def process_intent(from_number, data, original_text=""):
    session = session_manager.get_session(from_number)
    
    # Phase 4: Confirmation System
    if session["status"] == "awaiting_confirmation":
        text_lower = original_text.lower()
        if text_lower in ["yes", "y", "confirm", "ok", "send", "do it"]:
            execute_pending_action(from_number)
        elif text_lower in ["no", "n", "cancel", "stop", "edit"]:
            session_manager.clear_pending_action(from_number)
            send_text_message(from_number, "Action cancelled. You can continue editing the invoice.")
        else:
            send_text_message(from_number, "Please reply YES to confirm or NO to cancel.")
        return

    # Check if we are waiting for missing details
    queue = session.get("pending_item_fixes", [])
    if queue:
        text_lower = original_text.lower()
        if text_lower in ["cancel", "stop", "nevermind", "never mind", "skip"]:
            queue.pop(0)
            session["pending_item_fixes"] = queue
            send_text_message(from_number, "Okay, skipped that item.")
            process_pending_item_fixes(from_number)
            return
            
        import re
        nums = re.findall(r'\d+', text_lower.replace("k", "000").replace(",", ""))
        if nums:
            pending_item = queue[0]
            price_missing = pending_item.get("price") is None or pending_item.get("price") < 0
            qty_missing = pending_item.get("quantity") is None or pending_item.get("quantity") <= 0
            
            if price_missing and qty_missing and len(nums) >= 2:
                pending_item["quantity"] = int(nums[0])
                pending_item["price"] = float(nums[1])
            elif price_missing and not qty_missing and len(nums) >= 1:
                pending_item["price"] = float(nums[0])
            elif qty_missing and not price_missing and len(nums) >= 1:
                pending_item["quantity"] = int(nums[0])
            elif len(nums) == 1:
                pending_item["price"] = float(nums[0])
                pending_item["quantity"] = 1
                
            queue.pop(0)
            session["pending_item_fixes"] = queue
            session_manager.add_item(from_number, pending_item)
            process_pending_item_fixes(from_number)
            return

    intent = data.get("intent", "unknown")
    confidence = data.get("confidence", 1.0)
    entities = data.get("entities", {})

    if not check_confidence(confidence):
        send_text_message(from_number, "I didn't quite catch that. Could you rephrase what you want to do with the invoice?")
        return

    try:
        if intent == "create_invoice":
            session_manager.reset_session(from_number)
            handle_add_item(from_number, entities, is_create=True)
        elif intent == "add_item":
            handle_add_item(from_number, entities)
        elif intent == "update_item":
            handle_update_item(from_number, entities)
        elif intent == "remove_item":
            handle_remove_item(from_number, entities)
        elif intent == "set_client":
            handle_set_client(from_number, entities)
        elif intent in ["preview_invoice", "confirm_invoice", "send_invoice"]:
            handle_preview_and_confirm(from_number)
        elif intent == "cancel_invoice":
            session_manager.set_pending_action(from_number, "cancel_invoice")
            send_text_message(from_number, "Are you sure you want to cancel and clear this invoice? (YES/NO)")
        else:
            send_text_message(from_number, "I'm not sure how to handle that right now. Try adding an item or sending the invoice.")
    except Exception as e:
        print(f"Error: {e}")
        send_text_message(from_number, f"Error: {str(e)}")

def handle_add_item(from_number, entities, is_create=False):
    is_valid, err, valid_items, invalid_items = validate_add_item(entities)
    
    # If starting a new invoice but no items found, just set client
    if not is_valid and is_create and entities.get("client_name"):
        session_manager.set_client(from_number, {"name": entities["client_name"]})
        send_text_message(from_number, f"Started invoice for {entities['client_name']}. What are you selling?")
        return
        
    if not is_valid:
        send_text_message(from_number, err)
        return
        
    for item in valid_items:
        session_manager.add_item(from_number, item)
    
    if entities.get("client_name"):
        session_manager.set_client(from_number, {"name": entities["client_name"]})
        
    session = session_manager.get_session(from_number)
    
    if invalid_items:
        queue = session.get("pending_item_fixes", [])
        queue.extend(invalid_items)
        session["pending_item_fixes"] = queue
        
    process_pending_item_fixes(from_number)

def process_pending_item_fixes(from_number):
    session = session_manager.get_session(from_number)
    queue = session.get("pending_item_fixes", [])
    
    if queue:
        next_item = queue[0]
        price_missing = next_item.get("price") is None or next_item.get("price") < 0
        qty_missing = next_item.get("quantity") is None or next_item.get("quantity") <= 0
        
        if price_missing and qty_missing:
            msg = f"Please provide the quantity and price for '{next_item.get('name')}' in this format: (quantity, singleprice)"
        elif price_missing:
            msg = f"Please provide the price for '{next_item.get('name')}'."
        elif qty_missing:
            msg = f"Please provide the quantity for '{next_item.get('name')}'."
            
        send_text_message(from_number, msg)
    else:
        invoice = session.get("invoice", {})
        if invoice.get("items"):
            client_name = invoice.get("client", {}).get("name") if invoice.get("client") else None
            client_text = f" for {client_name}" if client_name else ""
            send_text_message(from_number, f"Item(s) added{client_text}. Current total is ₦{invoice.get('total', 0):,.0f}.\n\nSay 'send it' when you're done, or keep adding/editing items.")

def handle_update_item(from_number, entities):
    is_valid, err = validate_update_item(entities)
    if not is_valid:
        send_text_message(from_number, err)
        return
        
    target = entities["target_item_name"]
    price = entities.get("new_price")
    qty = entities.get("new_quantity")
    
    success, msg = session_manager.update_item(from_number, target, price, qty)
    send_text_message(from_number, msg)

def handle_remove_item(from_number, entities):
    is_valid, err = validate_remove_item(entities)
    if not is_valid:
        send_text_message(from_number, err)
        return
        
    success, msg = session_manager.remove_item(from_number, entities["target_item_name"])
    send_text_message(from_number, msg)

def handle_set_client(from_number, entities):
    if not entities.get("client_name"):
        send_text_message(from_number, "I couldn't detect the client's name.")
        return
    success, msg = session_manager.set_client(from_number, {"name": entities["client_name"]})
    if success:
        send_text_message(from_number, f"Client set to {entities['client_name']}.")
    else:
        send_text_message(from_number, msg)

def handle_preview_and_confirm(from_number):
    session = session_manager.get_session(from_number)
    invoice = session["invoice"]
    
    is_valid, err = validate_invoice_for_sending(invoice)
    if not is_valid:
        send_text_message(from_number, f"Cannot send yet: {err}")
        return
        
    # Phase 8: Invoice Review Step
    items_text = ""
    for item in invoice["items"]:
        items_text += f"• {item['quantity']}x {item['name']} — ₦{item['total']:,.0f}\n"
        
    preview = (
        f"📝 *Invoice Preview*\n\n"
        f"👤 *Client:* {invoice['client']['name']}\n"
        f"📦 *Items:*\n{items_text}\n"
        f"💰 *Subtotal:* ₦{invoice['subtotal']:,.0f}\n"
        f"💰 *VAT:* ₦{invoice['vat']:,.0f}\n"
        f"💰 *Total:* ₦{invoice['total']:,.0f}\n\n"
        f"Send this invoice? (Reply YES or NO)"
    )
    
    session_manager.set_pending_action(from_number, "send_invoice")
    send_text_message(from_number, preview)

def execute_pending_action(from_number):
    session = session_manager.get_session(from_number)
    action = session.get("pending_action")
    if not action:
        session_manager.update_status(from_number, "editing")
        return
        
    if action["type"] == "send_invoice":
        session_manager.clear_pending_action(from_number)
        finish_and_send_invoice(from_number)
    elif action["type"] == "cancel_invoice":
        session_manager.reset_session(from_number)
        send_text_message(from_number, "Invoice cancelled. You can start a new one anytime.")
    else:
        session_manager.clear_pending_action(from_number)


# --- BUSINESS SETUP ---
def start_business_setup(from_number):
    setup_sessions[from_number] = {"state": "AWAITING_BIZ_NAME"}
    send_text_message(from_number, "Business Setup: What is your Business Name?")

def process_biz_name(from_number, text):
    setup_sessions[from_number] = {"state": "AWAITING_BIZ_EMAIL", "biz_name": text}
    send_text_message(from_number, "Business Email?")

def process_biz_email(from_number, text):
    setup_sessions[from_number].update({"biz_email": text, "state": "AWAITING_BIZ_BANK1"})
    send_text_message(from_number, "Bank details? (Bank, Acc Number, Acc Name)")

def process_biz_bank1(from_number, text):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        send_text_message(from_number, "Provide Bank, Acc Number, Acc Name.")
        return
    setup_sessions[from_number].update({"bank1": parts, "state": "AWAITING_BIZ_BANK2"})
    send_text_message(from_number, "Second bank? (or 'none')")

def process_biz_bank2(from_number, text):
    if text.lower() != "none":
        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 3: setup_sessions[from_number]["bank2"] = parts
    setup_sessions[from_number]["state"] = "AWAITING_REFUND_POLICY"
    send_text_message(from_number, "Finally, let's set your Refund Policy. 📜\n\nType 'default' to use our standard policy, 'none' for no policy, or type out your custom policy.")

def process_refund_policy(from_number, text):
    session = setup_sessions[from_number]
    
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
    send_text_message(from_number, "Profile saved! ✅ You can now create invoices.")
    del setup_sessions[from_number]


def finish_and_send_invoice(from_number):
    session = session_manager.get_session(from_number)
    send_text_message(from_number, "Generating your invoice... ⏳")
    
    profile = get_business_profile(from_number)
    invoice = session["invoice"]
    
    # We pass the default 7.5 VAT since we calculated it in state_manager
    pdf_path = generate_pdf(profile, invoice["client"], invoice["items"], vat_rate=7.5)
    invoice_id = os.path.basename(pdf_path).split("_")[1].replace(".pdf", "")
    
    save_invoice_record(from_number, {
        "id": invoice_id, "client": invoice["client"], "items": invoice["items"],
        "vat_rate": 7.5, "total": invoice["total"],
        "is_paid": False, "timestamp": str(datetime.now())
    })
    
    media_id = upload_media(pdf_path).get("id")
    if media_id:
        send_document_message(from_number, media_id, os.path.basename(pdf_path))
        send_text_message(from_number, f"Invoice {invoice_id} sent! ✅ Type 'receipt' if paid.")
        
        # Lock session
        session_manager.update_status(from_number, "confirmed")
        session["last_invoice_id"] = invoice_id
    else:
        send_text_message(from_number, "Failed to upload invoice to WhatsApp.")
        session_manager.update_status(from_number, "editing")

def send_receipt(from_number):
    session = session_manager.get_session(from_number)
    inv_id = session.get("last_invoice_id")
    if not inv_id:
        send_text_message(from_number, "No recent invoice found to mark as paid.")
        return
        
    record = get_invoice_record(from_number, inv_id)
    if not record:
        return
        
    mark_invoice_as_paid(from_number, inv_id)
    profile = get_business_profile(from_number)
    path = generate_pdf(profile, record["client"], record["items"], is_receipt=True, vat_rate=record.get("vat_rate", 0.0))
    media_id = upload_media(path).get("id")
    if media_id: send_document_message(from_number, media_id, os.path.basename(path))

if __name__ == "__main__":
    app.run(port=5001, debug=True)

