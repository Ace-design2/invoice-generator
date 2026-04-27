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
    
    clean_msg = message.replace(",", "")

    # 1. Extract Person/Company Name (Strict)
    # Priority 1: Explicit markers "for", "to", "client is"
    match_explicit = re.search(r'(?:for|to|client|customer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message, re.IGNORECASE)
    if match_explicit:
        name = match_explicit.group(1).strip()
    else:
        # Priority 2: spaCy NER but check it's at the start or in a name-like context
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG"]:
                # Ignore common product-like names or if it's clearly an item list
                if not any(word in ent.text.lower() for word in ["refill", "soap", "roll", "plastic", "morn", "milo"]):
                    name = ent.text
                    break

    # 2. Extract Items with Prices
    # Pattern A: [Qty] [Item] [at/for/@/is] [Price] (Standard)
    # Pattern B: [Qty] [Item] [Price] (Shorthand: "2 Rice 2000")
    # Pattern C: [Item] [Price] (Shorthand: "Rice 2000")
    
    # We'll use a few passes
    
    # Pass 1: [Qty] [Item] [at/for/is/@] [Price]
    regex_a = re.finditer(r'(\d+)?\s*([a-zA-Z\s]{2,30}?) (?:at|for|is|@|costs)\s*(₦?[\d,kK]+)', clean_msg, re.IGNORECASE)
    for match in regex_a:
        qty = int(match.group(1)) if match.group(1) else 1
        item = match.group(2).strip()
        price_str = match.group(3).strip()
        price = parse_price(price_str)
        items_extracted.append({"name": item, "quantity": qty, "price": price, "total": qty * price})

    # Pass 2: [Item Name] [Numeric Price] (e.g. "Golden morn 4000")
    # Only if we haven't already extracted items or to catch leftovers
    if not items_extracted:
        # Avoid matching names as items
        lines = message.split("\n")
        for line in lines:
            line = line.strip()
            # Look for: [Item Name] [Price] or [Qty] [Item Name] [Price]
            match_b = re.search(r'^(\d+)?\s*([a-zA-Z\s]{2,20})\s+(\d+[kK]?)$', line, re.IGNORECASE)
            if match_b:
                qty = int(match_b.group(1)) if match_b.group(1) else 1
                item = match_b.group(2).strip()
                price = parse_price(match_b.group(3))
                if item.lower() not in ["none", "default", "yes", "no"]:
                    items_extracted.append({"name": item, "quantity": qty, "price": price, "total": qty * price})

    # 3. Simple Fallback for "2 laptops" (No price)
    if not items_extracted:
        simple_msg = re.sub(r'\(.*?\)', '', clean_msg)
        fallback_regex = re.finditer(r'(\d+)\s+([a-zA-Z]{2,20})', simple_msg)
        for match in fallback_regex:
            qty = int(match.group(1))
            item = match.group(2).strip()
            if name and item.lower() in name.lower(): continue
            items_extracted.append({"name": item, "quantity": qty, "price": 0, "total": 0})

    return {"name": name, "items": items_extracted}

def parse_price(price_str):
    price_str = price_str.lower().replace("₦", "").replace(",", "").strip()
    if price_str.endswith('k'):
        return float(price_str[:-1]) * 1000
    try:
        return float(price_str)
    except:
        return 0
