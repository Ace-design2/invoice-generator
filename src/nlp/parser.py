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
    
    # 1. Extract Person/Company Name (Strict)
    # Priority 1: Explicit markers "for", "to", "client is"
    match_explicit = re.search(r'(?:for|to|client|customer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s+(?:for|at|with|and|is)\b|\s*$)', message)
    if match_explicit:
        name = match_explicit.group(1).strip()
        message_for_items = message.replace(match_explicit.group(0), " ")
    else:
        # Priority 2: spaCy NER - only if we don't have explicit markers
        # AND only if it's very likely a name (not matching item patterns)
        message_for_items = message
        # If the message is short and looks like a list, don't guess names from NER
        if len(message.split('\n')) > 1 or ',' in message:
             pass 
        else:
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"]:
                    if not any(char.isdigit() for char in ent.text):
                        if not any(word in ent.text.lower() for word in ["refill", "soap", "roll", "plastic", "morn", "milo", "pizza", "burger", "laptop", "macbook", "iphone", "mouse", "hub"]):
                            name = ent.text
                            message_for_items = message.replace(name, " ")
                            break

    # Clean up command words from the start
    message_for_items = re.sub(r'^(?:generate|create|send|make)\s+(?:an?\s+)?(?:invoice|receipt)\s+(?:for\s+)?', '', message_for_items, flags=re.IGNORECASE).strip()

    # Split by common separators BEFORE removing commas from prices
    segments = re.split(r'and|,|\n|;', message_for_items, flags=re.IGNORECASE)
    
    for segment in segments:
        segment = segment.strip()
        if not segment: continue
        
        # Pattern A: [Qty] [Item] [at/for/@/is] [Price]
        match_a = re.search(r'(\d+)?\s*([a-zA-Z\s]{2,30}?) (?:at|for|is|@|costs)\s*(₦?[\d,kK]+)', segment, re.IGNORECASE)
        if match_a:
            qty = int(match_a.group(1)) if match_a.group(1) else 1
            item = match_a.group(2).strip()
            price = parse_price(match_a.group(3))
            if item.lower() not in ["", "for", "to", "a", "the", "invoice"]:
                items_extracted.append({"name": item, "quantity": qty, "price": price, "total": qty * price})
            continue

        # Pattern B: [Qty] [Item] [Price] (e.g. "3 Laptops 500k")
        match_b = re.search(r'^(\d+)\s+([a-zA-Z\s]{2,20})\s+(₦?[\d,kK]+)$', segment, re.IGNORECASE)
        if match_b:
            qty = int(match_b.group(1))
            item = match_b.group(2).strip()
            price = parse_price(match_b.group(3))
            items_extracted.append({"name": item, "quantity": qty, "price": price, "total": qty * price})
            continue
            
        # Pattern C: [Item] [Price] (e.g. "Laptops 500k")
        match_c = re.search(r'^([a-zA-Z\s]{2,20})\s+(₦?[\d,kK]+)$', segment, re.IGNORECASE)
        if match_c:
            item = match_c.group(1).strip()
            price = parse_price(match_c.group(2))
            if item.lower() not in ["none", "default", "yes", "no", "for", "to"]:
                items_extracted.append({"name": item, "quantity": 1, "price": price, "total": price})
            continue

        # Fallback: [Qty] [Item]
        match_f = re.search(r'^(\d+)\s+([a-zA-Z\s]{2,20})$', segment, re.IGNORECASE)
        if match_f:
            qty = int(match_f.group(1))
            item = match_f.group(2).strip()
            if name and item.lower() in name.lower(): continue
            items_extracted.append({"name": item, "quantity": qty, "price": 0, "total": 0})
            continue

        # Pattern D: [Price] [Item] (e.g. "15000 Sneakers")
        match_d = re.search(r'^(₦?[\d,kK]+)\s+([a-zA-Z\s]{2,20})$', segment, re.IGNORECASE)
        if match_d:
            price = parse_price(match_d.group(1))
            item = match_d.group(2).strip()
            items_extracted.append({"name": item, "quantity": 1, "price": price, "total": price})
            continue

        # Ultimate Fallback: Just [Item Name]
        if len(segment) > 1 and not segment.isdigit():
            # Avoid matching name as item
            if name and segment.lower() in name.lower(): continue
            # Avoid matching common filler words
            if segment.lower() in ["and", "for", "the", "with"]: continue
            items_extracted.append({"name": segment, "quantity": 1, "price": 0, "total": 0})

    return {"name": name, "items": items_extracted}

def parse_price(price_str):
    price_str = price_str.lower().replace("₦", "").replace(",", "").strip()
    if price_str.endswith('k'):
        return float(price_str[:-1]) * 1000
    try:
        return float(price_str)
    except:
        return 0
