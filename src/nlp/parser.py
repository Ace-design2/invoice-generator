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

def extract_invoice_data(message):
    """
    Consolidated entry point: Uses Gemini AI for entity extraction.
    """
    try:
        return extract_invoice_data_gemini(message)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Return empty structure as fallback
        return {"name": None, "items": []}

def extract_invoice_data_gemini(message):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Extract invoice details from this user message: "{message}"
    
    Return ONLY a JSON object with this exact structure:
    {{
      "name": "Client Name or null",
      "items": [
        {{
          "name": "Item description",
          "quantity": number,
          "price": number
        }}
      ]
    }}
    
    Rules:
    1. If a quantity is not mentioned, use 1.
    2. If a price is not mentioned, use 0.
    3. Prices like '50k' should be converted to 50000.
    4. Currency symbols like ₦ should be ignored/removed but the number kept.
    5. Be smart: '2 bags of rice at 30k' means quantity=2, price=30000.
    6. If you find a person's name or company being billed, put it in 'name'.
    """
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    # Clean up markdown JSON blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # If Gemini fails to return clean JSON, try to find it with regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except:
                return {"name": None, "items": []}
        else:
            return {"name": None, "items": []}
    
    # Ensure consistency with the rest of the app (total field)
    if "items" in data:
        for item in data["items"]:
            qty = item.get("quantity", 1)
            # Ensure quantity and price are numbers
            try:
                qty = float(qty)
            except:
                qty = 1
            
            price = item.get("price", 0)
            try:
                price = float(price)
            except:
                price = 0
                
            item["quantity"] = qty
            item["price"] = price
            item["total"] = qty * price
            
    return data

def extract_invoice_data_multimodal(file_path, mime_type):
    """
    Extracts invoice data from an image or audio file using Gemini.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Upload the file to Gemini File API
    uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
    
    prompt = """
    Extract invoice details from this media.
    - If it's an image: identify items, quantities, and prices (e.g. from a photo of products, a handwritten list, or a receipt).
    - If it's audio: transcribe the user's request for an invoice (who they are selling to and what).
    
    Return ONLY a JSON object with this exact structure:
    {
      "name": "Client Name or null",
      "items": [
        {
          "name": "Item description",
          "quantity": number,
          "price": number
        }
      ]
    }
    
    Rules:
    1. Default quantity to 1 if not specified.
    2. Default price to 0 if not specified.
    3. Return ONLY valid JSON. No other text.
    """
    
    response = model.generate_content([uploaded_file, prompt])
    text = response.text.strip()
    
    # Clean up markdown JSON blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # If Gemini fails to return clean JSON, try to find it with regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError("Could not parse JSON from Gemini response")
            
    # Ensure consistency with the rest of the app (total field)
    if "items" in data:
        for item in data["items"]:
            qty = item.get("quantity", 1)
            try:
                qty = float(qty)
            except:
                qty = 1
                
            price = item.get("price", 0)
            try:
                price = float(price)
            except:
                price = 0
                
            item["quantity"] = qty
            item["price"] = price
            item["total"] = qty * price
            
    return data
