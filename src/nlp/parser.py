import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key and api_key != "your_key_here":
    genai.configure(api_key=api_key)

import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key and api_key != "your_key_here":
    genai.configure(api_key=api_key)

INTENT_PROMPT_TEMPLATE = """
You are an AI assistant for a WhatsApp invoice generation bot.
Your job is to analyze the user's message and return a structured JSON object representing their intent.

Supported Intents:
- create_invoice: The user wants to start a new invoice or bill someone.
- add_item: The user wants to add an item(s) to the invoice.
- update_item: The user wants to change the price, quantity, or details of an existing item.
- remove_item: The user wants to remove an item from the invoice.
- set_client: The user specifies who the invoice is for.
- set_due_date: The user specifies a due date.
- apply_discount: The user wants to add a discount.
- apply_tax: The user wants to add VAT/Tax.
- preview_invoice: The user wants to see the current invoice.
- confirm_invoice: The user wants to finalize, confirm, or send the invoice.
- cancel_invoice: The user wants to cancel or reset the current invoice.
- unknown: The intent cannot be determined.

User Message: "{message}"

Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON):
{{
  "intent": "intent_name",
  "confidence": 0.95,
  "entities": {{
    "items": [
      {{
         "name": "Item name or null",
         "quantity": number or null,
         "price": number or null
      }}
    ],
    "client_name": "Name of the client if applicable, or null",
    "target_item_name": "If updating or removing, the name of the item to target, or null",
    "discount": number or null,
    "tax_rate": number or null,
    "new_price": number or null,
    "new_quantity": number or null
  }}
}}

Rules:
1. Prices like '50k' should be converted to 50000.
2. Ignore currency symbols like ₦.
3. Be smart: '2 bags of rice at 30k' means items=[{{"name": "rice", "quantity":2, "price":30000}}].
4. If they just say "Send it", the intent is confirm_invoice.
5. If they say "Change logo price to 60k", intent is update_item, target_item_name="logo", new_price=60000.
6. If they say "Remove the hoodie", intent is remove_item, target_item_name="hoodie".
7. If there are no items mentioned, "items" should be an empty list [].
"""

def clean_json_response(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {"intent": "unknown", "confidence": 0.0, "entities": {}}

def extract_intent(message):
    # Try multiple models if rate limited. Using Gemini 2.5 family per user info
    models_to_try = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro']
    
    last_error = None
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = INTENT_PROMPT_TEMPLATE.format(message=message)
            response = model.generate_content(prompt)
            return clean_json_response(response.text)
        except Exception as e:
            error_str = str(e)
            print(f"Gemini API Error ({model_name}): {error_str}")
            last_error = error_str
            if "429" in error_str or "quota" in error_str.lower() or "too many" in error_str.lower():
                print(f"Rate limit hit on {model_name}. Trying fallback model...")
                continue
            break # Break on non-429 errors
            
    print(f"All models failed or rate limited. Last Error: {last_error}")
    return {"intent": "unknown", "confidence": 0.0, "entities": {}}

def extract_intent_multimodal(file_path, mime_type):
    # Try multiple models if rate limited
    models_to_try = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro']
    last_error = None
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
            
            prompt = """
            You are an AI assistant for a WhatsApp invoice generation bot.
            Analyze this media and return a structured JSON object representing the user's intent.
            
            Supported Intents:
            - create_invoice: The user wants to start a new invoice or bill someone.
            - add_item: The user wants to add an item to the invoice.
            - update_item: The user wants to change the price, quantity, or details of an existing item.
            - remove_item: The user wants to remove an item from the invoice.
            - set_client: The user specifies who the invoice is for.
            - confirm_invoice: The user wants to finalize and send the invoice.
            - unknown: The intent cannot be determined.
            
            Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON):
            {
              "intent": "intent_name",
              "confidence": 0.95,
              "entities": {
                "items": [
                  {
                     "name": "Item name or null",
                     "quantity": number or null,
                     "price": number or null
                  }
                ],
                "client_name": "Name of the client if applicable, or null",
                "target_item_name": "If updating or removing, the name of the item to target, or null",
                "new_price": number or null,
                "new_quantity": number or null
              }
            }
            
            Rules:
            1. If it's an image of a receipt or product list, extract all items and put them in entities.items. intent: add_item or create_invoice.
            2. If it's audio, transcribe and classify the intent.
            3. Prices like '50k' should be converted to 50000.
            4. Ignore currency symbols like ₦.
            """
            
            response = model.generate_content([uploaded_file, prompt])
            return clean_json_response(response.text)
        except Exception as e:
            error_str = str(e)
            print(f"Gemini API Error Multimodal ({model_name}): {error_str}")
            last_error = error_str
            if "429" in error_str or "quota" in error_str.lower() or "too many" in error_str.lower():
                print(f"Rate limit hit on {model_name}. Trying fallback model...")
                continue
            break # Break on non-429 errors
            
    print(f"All models failed or rate limited. Last Error: {last_error}")
    return {"intent": "unknown", "confidence": 0.0, "entities": {}}

