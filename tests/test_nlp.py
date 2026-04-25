import json
from src.nlp.parser import extract_invoice_data

def run_tests():
    test_cases = [
        "Create an invoice for John for 50k",
        "Dr Martens 2",
        "Tshirt 5, Shoes 2",
        "Bill Sarah 150000",
        "Create an invoice for Michael",
        "Generate a bill for 75k",
        "5000",
        "Shoes 2\nSocks 5\nTies 3",
        "Invoice Segun for 150000",
        "I need an invoice for Mary. She bought 2 Laptops and 1 Mouse",
        "Custom Service 1",
        "Bill to: John Doe, Total: 15,000",
        "Generate bill for 50k for Sarah",
        "10 bags, 5 shoes, for Segun",
        "15000 for web design"
    ]

    print("========================================")
    print("           NLP PARSER TESTS")
    print("========================================\n")

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: '{test}'")
        try:
            data = extract_invoice_data(test)
            print("Output:")
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 40 + "\n")

if __name__ == "__main__":
    run_tests()
