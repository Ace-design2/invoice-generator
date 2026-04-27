import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_VERSION = os.getenv("API_VERSION", "v21.0")

BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}"

def send_text_message(to, text):
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=data)
    res_json = response.json()
    print(f"DEBUG: WhatsApp API Response (Text): {json.dumps(res_json, indent=2)}")
    return res_json

def upload_media(file_path):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/media"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    files = {
        "file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")
    }
    data = {
        "messaging_product": "whatsapp"
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    res_json = response.json()
    print(f"DEBUG: WhatsApp API Response (Media): {json.dumps(res_json, indent=2)}")
    return res_json

def send_document_message(to, media_id, filename):
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename
        }
    }
    response = requests.post(url, headers=headers, json=data)
    res_json = response.json()
    print(f"DEBUG: WhatsApp API Response (Document): {json.dumps(res_json, indent=2)}")
    return res_json
