import os
import json
from src.nlp.parser import extract_intent

def test_single_prompt():
    prompt = "Shaving stick 3k"
    print(f"Testing prompt: '{prompt}'")
    try:
        data = extract_intent(prompt)
        print("Output:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_single_prompt()
