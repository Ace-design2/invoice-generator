import spacy
import re

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading language model for the spacy POS tagger...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_invoice_data(message):
    doc = nlp(message)

    name = None
    items_extracted = []

    # 1. Extract Person/Company Name
    # Look for "for [Name]" or "to [Name]" patterns first
    match_for = re.search(r'(?:for|to|client|customer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message, re.IGNORECASE)
    if match_for:
        name = match_for.group(1).strip()
    else:
        # Fallback to spaCy NER
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG"] and not name:
                name = ent.text

    # 2. Item Extraction with Regex (Primary)
    # Pattern: [Qty] [Item Name] [at/for/@/is] [Price]
    # Example: "2 bags of rice at 5k" or "laptop for 200,000"
    # Also handle simple "Item at Price" (infer qty=1)
    
    # Clean up common separators to make regex easier
    clean_msg = message.replace(",", "")
    
    regex_items = re.finditer(r'(\d+)?\s*([a-zA-Z\s]{2,30}?) (?:at|for|is|@|costs)\s*(₦?[\d,kK]+)', clean_msg, re.IGNORECASE)
    
    for match in regex_items:
        qty_str = match.group(1)
        item_name = match.group(2).strip()
        price_str = match.group(3).strip()
        
        # Clean price
        price = 0
        p_match = re.search(r'(\d+)\s*[kK]\b', price_str)
        if p_match:
            price = float(p_match.group(1)) * 1000
        else:
            digits = re.sub(r'[^\d.]', '', price_str)
            price = float(digits) if digits else 0
            
        items_extracted.append({
            "name": item_name,
            "quantity": int(qty_str) if qty_str else 1, # Smart Default
            "price": price,
            "total": (int(qty_str) if qty_str else 1) * price
        })

    # 3. Simple Fallback for "2 laptops" (No price provided)
    if not items_extracted:
        # Look for [Qty] [Item] or just [Item]
        fallback_regex = re.finditer(r'(\d+)\s+([a-zA-Z\s]{2,20})', clean_msg)
        for match in fallback_regex:
            qty = int(match.group(1))
            item = match.group(2).strip()
            # Avoid picking up names as items
            if name and item.lower() in name.lower(): continue
            items_extracted.append({
                "name": item,
                "quantity": qty,
                "price": 0,
                "total": 0
            })

    return {
        "name": name,
        "items": items_extracted
    }
