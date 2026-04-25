# Skeleton for WhatsApp Bot Webhook
# This is where you would integrate with Twilio or Meta API

import os
from flask import Flask, request
from src.nlp.parser import extract_invoice_data
from src.core.generator import generate_pdf
from src.persistence.storage import get_company_details, load_clients

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    # 1. Get message from WhatsApp (e.g., from Twilio)
    # incoming_msg = request.values.get('Body', '').lower()
    # sender_phone = request.values.get('From', '')
    
    # 2. Extract data using NLP
    # data = extract_invoice_data(incoming_msg)
    
    # 3. Handle logic (Missing info prompts, etc.)
    
    # 4. Generate PDF
    # company = get_company_details()
    # client = ... # Load client by phone or name
    # pdf_path = generate_pdf(company, client, items)
    
    # 5. Send PDF back to WhatsApp
    
    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
