import sys
import os
import json
from unittest.mock import patch

# Adjust path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import app
from src.bot.state_manager import session_manager
from src.persistence.storage import save_business_profile

# Mock WhatsApp client to just print messages instead of sending them
def mock_send_text_message(to_number, text):
    print(f"\n[BOT -> {to_number}]:\n{text}\n")

app.send_text_message = mock_send_text_message

# Mock business profile to bypass setup
save_business_profile("1234567890", {
    "name": "Test Biz", "email": "test@biz.com", "phone": "1234567890",
    "bank1_name": "Test Bank", "bank1_account": "0000", "bank1_account_name": "Test",
    "refund_policy_text": "No refunds.", "location": "Lagos"
})

def simulate_message(text, mock_intent_data):
    print(f"==================================================")
    print(f"[USER -> Bot]: {text}")
    print(f"[MOCKED INTENT]: {mock_intent_data['intent']}")
    
    # We bypass handle_message so we don't hit Gemini at all,
    # and call process_intent directly.
    app.process_intent("1234567890", mock_intent_data, original_text=text)

def run_flow():
    # 1. Create Invoice
    simulate_message(
        "Create invoice for John for 2 laptops at 300k",
        {
            "intent": "create_invoice",
            "confidence": 0.99,
            "entities": {
                "client_name": "John",
                "items": [{"name": "laptop", "quantity": 2, "price": 300000}]
            }
        }
    )

    # 2. Add an item
    simulate_message(
        "Add 1 mouse for 15k",
        {
            "intent": "add_item",
            "confidence": 0.95,
            "entities": {
                "items": [{"name": "mouse", "quantity": 1, "price": 15000}]
            }
        }
    )

    # 3. Update an item
    simulate_message(
        "Change the laptop price to 350k",
        {
            "intent": "update_item",
            "confidence": 0.98,
            "entities": {
                "target_item_name": "laptop",
                "new_price": 350000
            }
        }
    )

    # 4. Remove an item
    simulate_message(
        "Actually, remove the mouse",
        {
            "intent": "remove_item",
            "confidence": 0.95,
            "entities": {
                "target_item_name": "mouse"
            }
        }
    )

    # 5. Review & Confirm
    simulate_message(
        "Send it",
        {
            "intent": "send_invoice",
            "confidence": 0.99,
            "entities": {}
        }
    )

    # 6. Confirm the action (YES)
    # The confirmation interceptor in process_intent uses original_text
    simulate_message(
        "yes",
        {
            "intent": "unknown", # NLP might not recognize just "yes"
            "confidence": 0.5,
            "entities": {}
        }
    )

    # 7. Try to edit a locked invoice
    simulate_message(
        "Change price to 400k",
        {
            "intent": "update_item",
            "confidence": 0.95,
            "entities": {
                "target_item_name": "laptop",
                "new_price": 400000
            }
        }
    )

if __name__ == "__main__":
    run_flow()
