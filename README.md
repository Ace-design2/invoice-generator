# WhatsApp Invoice Generator Bot

Organized Python application for generating professional invoices using NLP and Playwright.

## Structure

- `src/`: Core application logic.
  - `core/`: PDF generation and models.
  - `nlp/`: Natural Language Processing for invoice parsing.
  - `persistence/`: Data storage and retrieval.
  - `bot/`: WhatsApp bot integration (WIP).
- `data/`: JSON persistence files.
- `assets/`: Static assets like logos.
- `outputs/`: Generated PDF invoices.
- `tests/`: Unit and integration tests.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browser:
   ```bash
   playwright install chromium
   ```

## Usage

Run the CLI:
```bash
python3 main.py
```

## NLP Examples

You can enter commands like:
- "Create invoice for John for 50k"
- "Bill Sarah for 2 Laptops and 1 Mouse"
- "10 bags, 5 shoes, for Segun"
