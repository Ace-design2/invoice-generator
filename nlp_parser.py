import spacy
import re

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading language model for the spacy POS tagger\n(don't worry, this will only happen once)")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_invoice_data(message):
    doc = nlp(message)

    name = None
    amount = None

    # Extract names
    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name:
            name = ent.text

        if ent.label_ == "MONEY" and not amount:
            amount = ent.text

    # Cleanup amount if found by spacy
    if amount:
        match_k = re.search(r'(\d+)\s*k\b', amount, re.IGNORECASE)
        if match_k:
            amount = str(int(match_k.group(1)) * 1000)
        else:
            # Extract just digits from money string like "$500" or "50,000"
            digits = re.sub(r'[^\d]', '', amount)
            if digits:
                amount = digits

    # Backup amount detection
    if not amount:
        match_k = re.search(r'(\d+)\s*k\b', message, re.IGNORECASE)
        if match_k:
            amount = str(int(match_k.group(1)) * 1000)
        else:
            # Look for large numbers with commas
            match_comma = re.search(r'\d{1,3}(?:,\d{3})+', message)
            if match_comma:
                amount = re.sub(r'[^\d]', '', match_comma.group())
            else:
                # Removed generic \d+ matching so we don't accidentally grab item quantities as total amount
                pass

    # Backup name detection if spacy failed but there's a structure like "for John"
    if not name:
        match_for = re.search(r'for\s+([A-Z][a-z]+)', message)
        if match_for:
            name = match_for.group(1)

    items_extracted = []
    # If the message has multiple lines or commas, try to parse items like "Tshirt 5" or "5 Tshirt"
    parts = re.split(r'\n|,', message)
    for part in parts:
        part = part.strip()
        if not part: continue
        
        m1 = re.match(r'^([a-zA-Z][a-zA-Z\s]+?)\s+(\d+)$', part)
        if m1:
            items_extracted.append({'name': m1.group(1).strip(), 'quantity': int(m1.group(2))})
            continue
            
        m2 = re.match(r'^(\d+)\s+([a-zA-Z][a-zA-Z\s]+?)$', part)
        if m2:
            items_extracted.append({'name': m2.group(2).strip(), 'quantity': int(m2.group(1))})
            continue

    return {
        "name": name,
        "amount": amount,
        "items": items_extracted
    }

if __name__ == "__main__":
    message = "Create an invoice for John for 50k"
    data = extract_invoice_data(message)
    print(data)
