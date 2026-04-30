# WhatsApp Invoice Generator Bot

Organized Python application for generating professional invoices using Google's Gemini AI and Playwright. It supports both a command-line interface (CLI) and a WhatsApp bot integration capable of understanding text, images, and audio.

## Structure

- `src/`: Core application logic.
  - `core/`: PDF generation and Playwright logic.
  - `nlp/`: Natural Language Processing for invoice parsing using Gemini AI.
  - `persistence/`: Data storage and retrieval (JSON).
  - `bot/`: WhatsApp bot integration via Flask.
- `data/`: JSON persistence files.
- `assets/`: Static assets like logos and bank icons.
- `outputs/`: Generated PDF invoices.
- `tests/`: Unit and integration tests.

## Prerequisites

You need a Google Gemini API key. Create a `.env` file in the root directory and add:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
VERIFY_TOKEN=your_whatsapp_verify_token_here  # Required if running the WhatsApp bot
```

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

### Run the CLI
Use the interactive command-line interface to set up your business profile and generate invoices manually or via text prompts:
```bash
python3 main.py
```

### Run the WhatsApp Bot
Start the Flask server for the WhatsApp bot webhook:
```bash
python3 -m src.bot.app
```
*(Note: You will need a service like ngrok to expose your local server to the WhatsApp Cloud API during development.)*

## AI Capabilities

The bot uses the **Gemini AI** to parse invoice requests smartly. It supports multimodal inputs (via WhatsApp):
- **Text:** "Create invoice for John for 50k" or "Bill Sarah for 2 Laptops and 1 Mouse"
- **Images:** Send a photo of a handwritten list, receipt, or products.
- **Audio:** Send a voice note stating the client, items, and prices.
