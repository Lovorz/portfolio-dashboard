#!/usr/bin/env python3
import os
import re
import sys
import json
import base64
import glob
import argparse
import time
import shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
from dotenv import load_dotenv
import pypdf
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

# Load environment variables from .env
load_dotenv()

# Default JSON template for portfolio data
DEFAULT_PORTFOLIO_DATA = {
    "wealthx_funds": [
        {"t": "K-CHANGE-A(A)", "name": "K Positive Change Equity Fund", "theme": "Global ESG Growth", "units": 1250.5, "cost": 12.45, "nav": 13.80, "val": 17256, "pl": 1687, "pct": 10.8, "action": "hold", "urgency": "hold", "note": "Global sustainability ESG theme."},
        {"t": "ONE-UGG-RA", "name": "One Ultimate Global Growth Fund", "theme": "Global Disruptive Tech", "units": 850.0, "cost": 24.50, "nav": 21.20, "val": 18020, "pl": -2805, "pct": -13.5, "action": "hold", "urgency": "review", "note": "High growth, high valuation."}
    ],
    "dime_assets": [
        {"t": "AAPL", "shares": 5.5, "cost": 150.00, "price": 185.00, "val": 35612, "pl": 6687, "pct": 23.1, "action": "hold", "urgency": "hold", "note": "Core quality. Hold."},
        {"t": "NVDA", "shares": 10.0, "cost": 120.00, "price": 450.00, "val": 157500, "pl": 115500, "pct": 275.0, "action": "trim", "urgency": "trim", "note": "Trim on strength."},
        {"t": "VTI", "shares": 15.0, "cost": 230.00, "price": 240.00, "val": 126000, "pl": 5250, "pct": 4.3, "action": "hold", "urgency": "hold", "note": "US Total Market Index ETF."}
    ],
    "cash": {
        "now": 33600,
        "target": 58500
    },
    "trim_rules": [
        {"ticker": "NVDA", "pct": "+150%", "rule": "ถ้า position ใหญ่เกิน 10% ของพอร์ต ให้ trim 20%", "urgency": "urgent"},
        {"ticker": "AAPL", "pct": "+50%", "rule": "ถ้าสัดส่วนกำไรเกิน 50% ให้ขายดึงทุนคืนมาส่วนหนึ่ง", "urgency": "watch"}
    ],
    "review_rules": [
        {"ticker": "SOFI", "loss": "-15%", "rule": "ถ้าลงเกิน -20% จากทุน ให้ตัดขาดทุน", "urgency": "high"},
        {"ticker": "TSLA", "loss": "-20%", "rule": "ทบทวนปัจจัยพื้นฐานหากราคากดต่ำกว่า $150", "urgency": "watch"}
    ],
    "ideas": [
        {"t": "CRWD", "name": "CrowdStrike", "theme": "Cybersecurity SaaS", "cat": "gap", "why": "ผู้นำด้าน AI Cybersecurity เติบโตเด่น", "entry": "$340–360", "entryLow": 340.0, "entryHigh": 360.0, "dca": "฿8,000–12,000", "priority": "high"},
        {"t": "TSLA", "name": "Tesla", "theme": "EV & Robotics", "cat": "watch", "why": "รอจังหวะราคาปรับฐานสะสมเพิ่มเติม", "entry": "$160–180", "entryLow": 160.0, "entryHigh": 180.0, "dca": "฿5,000–10,000", "priority": "medium"},
        {"t": "PLTR", "name": "Palantir", "theme": "AI Platforms", "cat": "quality", "why": "ความต้องการใช้ AIP เพิ่มสูงขึ้นมากในเชิงพาณิชย์", "entry": "$20–22", "entryLow": 20.0, "entryHigh": 22.0, "dca": "฿4,000–6,000", "priority": "high"}
    ],
    "yt_channels": [
        {"name": "Dime! กองทุนและหุ้นต่างประเทศ", "handle": "@dimeinvestment", "channelId": "", "emoji": "💰", "color": "#10b981"},
        {"name": "Money Buffalo", "handle": "@moneybuffalo", "channelId": "", "emoji": "🐂", "color": "#f59e0b"},
        {"name": "The Standard Wealth", "handle": "@thestandardwealth", "channelId": "", "emoji": "📰", "color": "#ef4444"}
    ],
    "investor_profile": {
        "age": 28,
        "income": 65000,
        "expense": 35000,
        "goal": "อิสรภาพทางการเงินใน 10 ปี เน้นสะสมหุ้นเติบโตและ ETF ปันผลสะสม"
    },
    "transactions": []
}

PORTFOLIO_FILE = "portfolio_data.json"
TRANSACTIONS_FILE = "transactions.json"

def get_portfolio_data():
    """Load existing portfolio data or return default if missing."""
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {PORTFOLIO_FILE}: {e}. Using default template.")
    return DEFAULT_PORTFOLIO_DATA.copy()

def get_transactions():
    """Load transaction log or return empty list if missing."""
    if os.path.exists(TRANSACTIONS_FILE):
        try:
            with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {TRANSACTIONS_FILE}: {e}. Using empty list.")
    return []

def save_data(portfolio, transactions):
    """Save updated data files."""
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, indent=2, ensure_ascii=False)
        with open(TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        print(f"✅ Data saved successfully to {PORTFOLIO_FILE} and {TRANSACTIONS_FILE}!")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def decrypt_pdf(input_path, output_path, password):
    """Decrypt a password-protected PDF using pypdf."""
    print(f"🔓 Decrypting PDF: {input_path}")
    try:
        reader = pypdf.PdfReader(input_path)
        if reader.is_encrypted:
            status = reader.decrypt(password)
            if status == 0:
                raise ValueError("Decryption failed. Incorrect password provided.")
        
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        with open(output_path, "wb") as f:
            writer.write(f)
        print(f"✨ Decrypted PDF saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ PDF Decryption Error: {e}")
        return False

def call_mistral_with_retry(api_func, *args, **kwargs):
    """Call a Mistral API function, retrying with backoff if rate limited (429)."""
    max_retries = 5
    delay = 3
    for attempt in range(max_retries):
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Rate limit" in err_str or "rate_limited" in err_str or "rate limit" in err_str.lower():
                print(f"⚠️ Mistral Rate Limit hit. Retrying in {delay} seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
    raise Exception("Failed after maximum retries due to Mistral Rate Limits")

def ocr_and_extract_transactions(pdf_path, mistral_api_key):
    """Upload decrypted PDF to Mistral OCR, get text, then parse using Mistral Chat API."""
    if not mistral_api_key:
        print("❌ MISTRAL_API_KEY is not set.")
        return None

    print(f"👁️ Sending {pdf_path} to Mistral OCR API...")
    try:
        client = Mistral(api_key=mistral_api_key)
        
        # 1. Upload PDF to Mistral
        with open(pdf_path, "rb") as f:
            uploaded_file = call_mistral_with_retry(
                client.files.upload,
                file={"file_name": os.path.basename(pdf_path), "content": f},
                purpose="ocr"
            )
        
        # 2. Process OCR
        ocr_response = call_mistral_with_retry(
            client.ocr.process,
            model="mistral-ocr-latest",
            document={"file_id": uploaded_file.id}
        )
        
        # Combine markdown from all pages
        full_ocr_text = ""
        for page in ocr_response.pages:
            full_ocr_text += page.markdown + "\n\n"
        
        print("📝 OCR extracted successfully. Raw markdown length:", len(full_ocr_text))
        
        # 3. Structure the data using Chat Completion
        system_prompt = """
You are an expert financial assistant. Your task is to extract transaction records from the provided OCR text of a stock/ETF/Mutual Fund trading confirmation statement (from either Dime! or WealthX apps).
Extract the following fields for each transaction and return them in a valid JSON list.

Schema for each transaction object:
{
  "source": "string ('Dime' or 'WealthX')", // The platform name, identified from the document header or text
  "invoice_no": "string or null", // เลขที่ใบกำกับภาษี / invoice number (e.g. DIME0320250530004118 or similar)
  "invoice_date": "string (DD/MM/YYYY) or null", // วันที่ออกใบกำกับภาษี / invoice date
  "order_id": "string or null", // เลขที่คำสั่ง / order ID
  "settlement_date": "string (DD/MM/YYYY) or null", // วันที่ครบกำหนดชำระ / settlement date
  "transaction_type": "string ('BUY' or 'SEL')", // ประเภทการซื้อขาย: BUY (ซื้อ) or SEL (ขาย)
  "ticker": "string", // ชื่อหลักทรัพย์ / Ticker symbol (e.g. AAPL, VTI) or Fund code (e.g. K-CHANGE-A(A), ONE-UGG-RA)
  "exchange": "string or null", // ตลาด / exchange (e.g. XNAS, XNYS, or null for mutual funds)
  "units": float, // จำนวนหน่วย / quantity / units
  "unit_price": float, // ราคาต่อหน่วย / unit price / NAV per unit
  "currency": "string", // สกุลเงิน / currency (e.g. USD, THB)
  "gross_amount": float, // จำนวนเงิน / gross amount in currency
  "fee": float, // ค่าธรรมเนียม รวม VAT / fee include VAT (usually in THB)
  "withholding_tax": float, // ภาษีหัก ณ ที่จ่าย / withholding tax (usually in THB)
  "total_amount_ccy": float, // จำนวนเงินสุทธิ / total amount in main currency
  "total_amount_thb": float // จำนวนเงินสุทธิรวม / total amount in THB
}

Please output ONLY the JSON array inside a ```json and ``` block. Do not write any other explanations.
"""
        print("🤖 Call LLM to structure transactions...")
        chat_response = call_mistral_with_retry(
            client.chat.complete,
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract transaction details from this OCR text:\n\n{full_ocr_text}"}
            ]
        )
        
        raw_content = chat_response.choices[0].message.content
        
        # Clean up JSON block
        json_match = re.search(r"```json\s*(.*?)\s*```", raw_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw_content.strip()
            
        transactions = json.loads(json_str)
        print(f"🎉 Successfully parsed {len(transactions)} transaction(s)!")
        return transactions

    except Exception as e:
        print(f"❌ Error in OCR / Parsing pipeline: {e}")
        return None

def rebuild_portfolio_from_transactions(portfolio, transactions, new_transactions=None):
    """Rebuild the entire portfolio holdings from scratch based on the transaction history,
    sorted chronologically, and filtering out assets that have been sold out."""
    from datetime import datetime
    
    def parse_date(date_str):
        if not date_str:
            return datetime.min.date()
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if year > 2500:
                    year -= 543
                return datetime(year, month, day).date()
        except Exception:
            pass
        return datetime.min.date()

    # Sort the complete transaction list chronologically
    sorted_txs = sorted(transactions, key=lambda x: parse_date(x.get("invoice_date") or x.get("settlement_date")))

    wealthx_funds = {}
    dime_assets = {}
    
    for tx in sorted_txs:
        source = tx.get("source", "Dime")  # Dime or WealthX
        ticker = tx.get("ticker")
        tx_type = tx.get("transaction_type")
        units = tx.get("units", 0) or 0.0
        unit_price = tx.get("unit_price", 0) or 0.0
        
        if not ticker or not tx_type:
            continue
            
        if source == "WealthX":
            if ticker not in wealthx_funds:
                existing_fund = next((f for f in portfolio.get("wealthx_funds", []) if f["t"] == ticker), {})
                wealthx_funds[ticker] = {
                    "t": ticker,
                    "name": existing_fund.get("name") or tx.get("name") or f"Mutual Fund {ticker}",
                    "theme": existing_fund.get("theme") or tx.get("theme") or "Global Fund",
                    "units": 0.0,
                    "cost": 0.0,
                    "nav": existing_fund.get("nav") or unit_price,
                    "val": 0,
                    "pl": 0,
                    "pct": 0.0,
                    "action": existing_fund.get("action") or "hold",
                    "urgency": existing_fund.get("urgency") or "hold",
                    "note": existing_fund.get("note") or "Imported from WealthX statement"
                }
            
            fund = wealthx_funds[ticker]
            old_units = fund.get("units", 0.0)
            old_cost = fund.get("cost", 0.0)
            
            if tx_type == "BUY":
                new_units = old_units + units
                if new_units > 0:
                    new_cost = (old_units * old_cost + units * unit_price) / new_units
                else:
                    new_cost = 0.0
                fund["units"] = new_units
                fund["cost"] = new_cost
                fund["nav"] = unit_price
            elif tx_type == "SEL":
                fund["units"] = max(0.0, old_units - units)
                
        else: # Dime
            if ticker not in dime_assets:
                existing_asset = next((a for a in portfolio.get("dime_assets", []) if a["t"] == ticker), {})
                dime_assets[ticker] = {
                    "t": ticker,
                    "shares": 0.0,
                    "cost": 0.0,
                    "price": existing_asset.get("price") or unit_price,
                    "currency": existing_asset.get("currency") or tx.get("currency", "USD"),
                    "val": 0,
                    "pl": 0,
                    "pct": 0.0,
                    "action": existing_asset.get("action") or "hold",
                    "urgency": existing_asset.get("urgency") or "hold",
                    "note": existing_asset.get("note") or "Imported from Dime statement"
                }
                
            asset = dime_assets[ticker]
            shares = asset.get("shares", 0.0)
            cost = asset.get("cost", 0.0)
            
            if tx_type == "BUY":
                new_shares = shares + units
                if new_shares > 0:
                    new_cost = (shares * cost + units * unit_price) / new_shares
                else:
                    new_cost = 0.0
                asset["shares"] = new_shares
                asset["cost"] = new_cost
                asset["price"] = unit_price
            elif tx_type == "SEL":
                asset["shares"] = max(0.0, shares - units)

    # After replaying, overwrite with existing prices if available, and filter out sold-out assets
    existing_wealthx_nav = {f["t"]: f["nav"] for f in portfolio.get("wealthx_funds", []) if "nav" in f}
    existing_dime_price = {a["t"]: a["price"] for a in portfolio.get("dime_assets", []) if "price" in a}

    for ticker, fund in list(wealthx_funds.items()):
        # Filter out assets with units <= 0.00001
        if fund["units"] <= 0.00001:
            del wealthx_funds[ticker]
            continue
            
        if ticker in existing_wealthx_nav:
            fund["nav"] = existing_wealthx_nav[ticker]
            
        # Recalculate values
        fund["val"] = int(fund["units"] * fund["nav"])
        cost_val = fund["units"] * fund["cost"]
        fund["pl"] = int(fund["val"] - cost_val)
        fund["pct"] = round((fund["pl"] / cost_val * 100) if cost_val > 0 else 0.0, 1)

    for ticker, asset in list(dime_assets.items()):
        # Filter out assets with shares <= 0.00001
        if asset["shares"] <= 0.00001:
            del dime_assets[ticker]
            continue
            
        if ticker in existing_dime_price:
            asset["price"] = existing_dime_price[ticker]
            
        # Recalculate values based on currency
        currency = asset.get("currency", "USD")
        if currency == "THB":
            asset["val"] = int(asset["shares"] * asset["price"])
            cost_val = asset["shares"] * asset["cost"]
        else:
            asset["val"] = int(asset["shares"] * asset["price"] * 35.0) # Assume FX 35 as fallback
            cost_val = asset["shares"] * asset["cost"] * 35.0
            
        asset["pl"] = int(asset["val"] - cost_val)
        asset["pct"] = round((asset["pl"] / cost_val * 100) if cost_val > 0 else 0.0, 1)

    portfolio["wealthx_funds"] = list(wealthx_funds.values())
    portfolio["dime_assets"] = list(dime_assets.values())

    # Update cash balance incrementally based on new transactions
    cash_now = portfolio.get("cash", {}).get("now", 0)
    if new_transactions:
        for tx in new_transactions:
            tx_type = tx.get("transaction_type")
            total_thb = tx.get("total_amount_thb", 0)
            if tx_type == "BUY":
                cash_now -= total_thb
            elif tx_type == "SEL":
                cash_now += total_thb
    portfolio["cash"]["now"] = int(max(0, cash_now))
    
    return portfolio


def filter_duplicate_transactions(existing_txs, new_txs):
    """Filters out new transactions that already exist in the database using invoice, order ID,
    or unique transaction property hashes (standardizing dates, tickers, types, units, and price)."""
    existing_invoices = {t["invoice_no"] for t in existing_txs if t.get("invoice_no")}
    existing_orders = {t["order_id"] for t in existing_txs if t.get("order_id")}
    
    def get_tx_hash(tx):
        date_str = tx.get("invoice_date") or tx.get("settlement_date")
        date_normalized = ""
        if date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                try:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    if year > 2500:
                        year -= 543
                    date_normalized = f"{day:02d}/{month:02d}/{year}"
                except:
                    date_normalized = date_str
            else:
                date_normalized = date_str
        
        ticker = tx.get("ticker", "")
        tx_type = tx.get("transaction_type", "")
        units = round(tx.get("units") or 0.0, 5)
        price = round(tx.get("unit_price") or 0.0, 4)
        return (date_normalized, ticker, tx_type, units, price)
        
    existing_hashes = {get_tx_hash(t) for t in existing_txs}
    
    filtered = []
    for tx in new_txs:
        inv = tx.get("invoice_no")
        ord_id = tx.get("order_id")
        
        if (inv and inv in existing_invoices) or (ord_id and ord_id in existing_orders):
            print(f"⚠️ Skipping duplicate transaction (invoice: {inv}, order: {ord_id})")
            continue
            
        tx_hash = get_tx_hash(tx)
        if tx_hash in existing_hashes:
            print(f"⚠️ Skipping duplicate transaction by property hash: {tx_hash[0]} {tx_hash[1]} {tx_hash[2]}")
            continue
            
        filtered.append(tx)
        if inv:
            existing_invoices.add(inv)
        if ord_id:
            existing_orders.add(ord_id)
        existing_hashes.add(tx_hash)
        
    return filtered

def get_gmail_service():
    """Gets or refreshes Gmail API service credentials."""
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"⚠️ Error loading token.json: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Error refreshing token: {e}")
                creds = None

        if not creds:
            secret_files = glob.glob("client_secret_*.json")
            if not secret_files:
                print("❌ No client_secret_*.json found in current directory.")
                return None
            client_secret_path = secret_files[0]
            print(f"🔑 Found client secret file: {client_secret_path}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"⚠️ Failed to open browser automatically: {e}")
                print("💡 Retrying with manual copy-paste mode (open_browser=False)...")
                creds = flow.run_local_server(port=0, open_browser=False)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def process_gmail(pdf_password, mistral_api_key, sync_all=False):
    """Fetch trade confirmations via Gmail REST API, decrypt PDFs, run Mistral OCR, and update database."""
    print("📧 Connecting to Gmail via REST API...")
    try:
        service = get_gmail_service()
        if not service:
            print("❌ Gmail service could not be initialized.")
            return []
            
        # Search query for emails matching Dime or WealthX
        if sync_all:
            query = '("Dime" OR "WealthX" OR "ใบยืนยันการซื้อขาย" OR "confirming trading" OR "ใบยืนยันรายการซื้อขาย" OR "ใบยืนยันการทำรายการ" OR "เวลธ์ เอกซ์") has:attachment filename:pdf'
            print("🔄 Syncing ALL matching emails (from the beginning)...")
        else:
            query = 'is:unread ("Dime" OR "WealthX" OR "ใบยืนยันการซื้อขาย" OR "confirming trading" OR "ใบยืนยันรายการซื้อขาย" OR "ใบยืนยันการทำรายการ" OR "เวลธ์ เอกซ์") has:attachment filename:pdf'
            print("🔄 Syncing UNREAD matching emails...")
        print(f"🔍 Searching with query: {query}")
        
        messages = []
        next_page_token = None
        while True:
            results = service.users().messages().list(userId='me', q=query, pageToken=next_page_token).execute()
            messages.extend(results.get('messages', []))
            next_page_token = results.get('nextPageToken')
            if not next_page_token or (not sync_all and len(messages) >= 100):
                break
        
        if not messages:
            print("📭 No matching messages found.")
            return []
            
        print(f"📥 Found {len(messages)} matching email(s) with PDF statements. Processing...")
        all_new_transactions = []
        
        for msg_info in messages:
            msg_id = msg_info['id']
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            # Extract Subject
            headers = msg.get('payload', {}).get('headers', [])
            subject = ""
            for h in headers:
                if h['name'].lower() == 'subject':
                    subject = h['value']
                    break
            
            print(f"📩 Email Subject: {subject}")
            
            payload = msg.get('payload', {})
            flat_parts = []
            
            # Helper function to recursively retrieve all message parts
            def get_all_parts(part, parts_list):
                if 'parts' in part:
                    for subpart in part['parts']:
                        get_all_parts(subpart, parts_list)
                else:
                    parts_list.append(part)
            
            get_all_parts(payload, flat_parts)
            
            decryption_failed = False
            ocr_failed = False
            for part in flat_parts:
                filename = part.get('filename')
                mime_type = part.get('mimeType')
                
                # Check if it's a PDF attachment
                if filename and (filename.lower().endswith('.pdf') or mime_type == 'application/pdf'):
                    print(f"📎 Downloading attachment: {filename}")
                    body = part.get('body', {})
                    attachment_id = body.get('attachmentId')
                    
                    if attachment_id:
                        attachment = service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=attachment_id
                        ).execute()
                        
                        data = attachment.get('data')
                        if data:
                            pdf_data = base64.urlsafe_b64decode(data.encode('utf-8'))
                            
                            temp_encrypted = "temp_encrypted.pdf"
                            temp_decrypted = "temp_decrypted.pdf"
                            
                            with open(temp_encrypted, "wb") as f:
                                f.write(pdf_data)
                                
                            # Decrypt
                            decrypted_success = decrypt_pdf(temp_encrypted, temp_decrypted, pdf_password)
                            
                            if decrypted_success:
                                # Save decrypted PDF to documents folder
                                docs_dir = "/mnt/d/Ubuntu_data/portfolio/documents"
                                os.makedirs(docs_dir, exist_ok=True)
                                dest_path = os.path.join(docs_dir, filename)
                                shutil.copy2(temp_decrypted, dest_path)
                                print(f"📁 Saved decrypted PDF statement to: {dest_path}")
                                
                                # Run OCR
                                txs = ocr_and_extract_transactions(temp_decrypted, mistral_api_key)
                                if txs is not None:
                                    all_new_transactions.extend(txs)
                                else:
                                    ocr_failed = True
                                
                                # Clean up decrypted file for security
                                if os.path.exists(temp_decrypted):
                                    os.remove(temp_decrypted)
                            else:
                                decryption_failed = True
                                    
                            # Clean up encrypted file
                            if os.path.exists(temp_encrypted):
                                os.remove(temp_encrypted)
            
            # Mark email as read by removing the UNREAD label only if BOTH decryption and OCR succeeded
            if not decryption_failed and not ocr_failed:
                print(f"🏷️ Marking message {msg_id} as read...")
                service.users().messages().batchModify(
                    userId='me',
                    body={
                        'ids': [msg_id],
                        'removeLabelIds': ['UNREAD']
                    }
                ).execute()
            else:
                print(f"⚠️ Keeping message {msg_id} as UNREAD because processing failed (decryption_failed: {decryption_failed}, ocr_failed: {ocr_failed}).")
            
            # Delay to avoid hammering Mistral API and hitting rate limits
            time.sleep(2)
            
        return all_new_transactions
        
    except Exception as e:
        print(f"❌ Gmail REST API Error: {e}")
        return []

def generate_tax_report(transactions):
    """Generates a tax report (markdown and JSON) summarizing transaction values, capital gains, fees, and withholding taxes."""
    print("📊 Generating Tax Report...")
    
    holding_units = {}
    holding_cost = {}
    tax_records = []
    
    from datetime import datetime
    
    def get_tx_date(tx):
        date_str = tx.get("invoice_date") or tx.get("settlement_date")
        if date_str:
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    if year > 2500:
                        year -= 543
                    return datetime(year, month, day).date()
            except:
                pass
        return datetime.min.date()
        
    sorted_txs = sorted(transactions, key=get_tx_date)
    annual_summary = {}
    
    for tx in sorted_txs:
        source = tx.get("source", "Dime")
        ticker = tx.get("ticker")
        tx_type = tx.get("transaction_type")
        units = tx.get("units", 0)
        unit_price = tx.get("unit_price", 0)
        total_thb = tx.get("total_amount_thb", 0)
        fee = tx.get("fee", 0)
        wht = tx.get("withholding_tax", 0)
        date_str = tx.get("invoice_date") or tx.get("settlement_date")
        
        if not ticker or not tx_type or not date_str:
            continue
            
        try:
            parts = date_str.split('/')
            year = int(parts[2])
            if year > 2500:
                year -= 543
        except:
            year = 2026
            
        if year not in annual_summary:
            annual_summary[year] = {
                "capital_gain_thb": 0.0,
                "fee_thb": 0.0,
                "wht_thb": 0.0,
                "total_buys_thb": 0.0,
                "total_sells_thb": 0.0
            }
            
        annual_summary[year]["fee_thb"] += fee
        annual_summary[year]["wht_thb"] += wht
        
        gain_thb = 0.0
        cost_basis_thb = 0.0
        
        if tx_type == "BUY":
            annual_summary[year]["total_buys_thb"] += total_thb
            old_units = holding_units.get(ticker, 0.0)
            old_cost = holding_cost.get(ticker, 0.0)
            
            new_units = old_units + units
            if new_units > 0:
                new_cost = (old_units * old_cost + total_thb) / new_units
            else:
                new_cost = 0.0
            holding_units[ticker] = new_units
            holding_cost[ticker] = new_cost
            
        elif tx_type == "SEL":
            annual_summary[year]["total_sells_thb"] += total_thb
            old_units = holding_units.get(ticker, 0.0)
            avg_cost = holding_cost.get(ticker, 0.0)
            
            cost_basis_thb = units * avg_cost
            gain_thb = total_thb - cost_basis_thb
            
            annual_summary[year]["capital_gain_thb"] += gain_thb
            holding_units[ticker] = max(0.0, old_units - units)
            
        tax_records.append({
            "date": date_str,
            "source": source,
            "ticker": ticker,
            "type": tx_type,
            "units": units,
            "unit_price": unit_price,
            "total_thb": total_thb,
            "cost_basis_thb": round(cost_basis_thb, 2) if tx_type == "SEL" else 0.0,
            "capital_gain_thb": round(gain_thb, 2) if tx_type == "SEL" else 0.0,
            "fee_thb": fee,
            "wht_thb": wht
        })
        
    report_data = {
        "annual_summary": annual_summary,
        "records": tax_records
    }
    
    with open("tax_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
        
    md_content = """# 📊 รายงานภาษีการลงทุนต่างประเทศ (Tax Report)
รายงานนี้สรุปธุรกรรมการซื้อขาย กำไรส่วนต่างทุน (Capital Gains) ค่าธรรมเนียม และภาษีหัก ณ ที่จ่าย สำหรับยื่นแสดงภาษีเงินได้บุคคลธรรมดา (สรรพากร)

## 📅 ตารางสรุปรายปี (Annual Summary)
| ปี (Year) | มูลค่าการซื้อรวม (Total Buys) | มูลค่าการขายรวม (Total Sells) | กำไร/ขาดทุนจากส่วนต่างทุน (Capital Gain/Loss) | ค่าธรรมเนียมรวม (Total Fees) | ภาษีหัก ณ ที่จ่ายสะสม (Total Withholding Tax) |
|---|---|---|---|---|---|
"""
    for year, summary in sorted(annual_summary.items()):
        md_content += f"| {year} | ฿{summary['total_buys_thb']:,.2f} | ฿{summary['total_sells_thb']:,.2f} | ฿{summary['capital_gain_thb']:,.2f} | ฿{summary['fee_thb']:,.2f} | ฿{summary['wht_thb']:,.2f} |\n"
        
    md_content += """
## 📝 รายละเอียดธุรกรรม (Transaction Details)
| วันที่ (Date) | แพลตฟอร์ม (Source) | หลักทรัพย์ (Asset) | ประเภท (Type) | จำนวนหน่วย (Units) | ราคา/หน่วย | มูลค่ารวม (THB) | ต้นทุนฝั่งขาย (Cost Basis) | กำไรจากทุน (Capital Gain) | ค่าธรรมเนียม (Fee) | ภาษีหัก ณ ที่จ่าย (WHT) |
|---|---|---|---|---|---|---|---|---|---|---|
"""
    for rec in sorted(tax_records, key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y")):
        type_th = "ซื้อ (BUY)" if rec["type"] == "BUY" else "ขาย (SEL)"
        cost_str = f"฿{rec['cost_basis_thb']:,.2f}" if rec["type"] == "SEL" else "-"
        gain_str = f"฿{rec['capital_gain_thb']:,.2f}" if rec["type"] == "SEL" else "-"
        
        md_content += f"| {rec['date']} | {rec['source']} | {rec['ticker']} | {type_th} | {rec['units']:.5f} | {rec['unit_price']:.2f} | ฿{rec['total_thb']:,.2f} | {cost_str} | {gain_str} | ฿{rec['fee_thb']:,.2f} | ฿{rec['wht_thb']:,.2f} |\n"
        
    with open("tax_report.md", "w", encoding="utf-8") as f:
        f.write(md_content)
        
    import csv
    csv_file = "tax_report_สรรพากร.csv"
    try:
        with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ลำดับ", "วันที่ (Date)", "แหล่งข้อมูล (Source)", "ชื่อย่อสินทรัพย์ (Asset)",
                "ประเภท (Type)", "จำนวนหน่วย (Units)", "ราคา/หน่วย (Unit Price)",
                "มูลค่าธุรกรรมบาท (Total THB)", "ต้นทุนฝั่งขายบาท (Cost Basis THB)",
                "กำไรส่วนต่างบาท (Capital Gain THB)", "ค่าธรรมเนียมบาท (Fee THB)",
                "ภาษีหัก ณ ที่จ่ายบาท (WHT THB)"
            ])
            for idx, rec in enumerate(sorted(tax_records, key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y")), 1):
                type_th = "ซื้อ (BUY)" if rec["type"] == "BUY" else "ขาย (SEL)"
                writer.writerow([
                    idx,
                    rec["date"],
                    rec["source"],
                    rec["ticker"],
                    type_th,
                    f"{rec['units']:.5f}",
                    f"{rec['unit_price']:.4f}",
                    round(rec["total_thb"], 2),
                    round(rec["cost_basis_thb"], 2) if rec["type"] == "SEL" else 0.0,
                    round(rec["capital_gain_thb"], 2) if rec["type"] == "SEL" else 0.0,
                    round(rec["fee_thb"], 2),
                    round(rec["wht_thb"], 2)
                ])
    except Exception as e:
        print(f"❌ Error exporting CSV tax report: {e}")
        
    print("✅ Tax Report generated successfully as tax_report.json, tax_report.md, and tax_report_สรรพากร.csv!")

def main():
    parser = argparse.ArgumentParser(description="Dime Portfolio Gmail Sync & OCR Tool (Mistral AI)")
    parser.add_argument("--pdf", help="Path to a local password-protected Dime trade confirmation PDF for manual processing.")
    parser.add_argument("--password", help="Password to decrypt the PDF. Overrides DIME_PDF_PASSWORD env var.")
    parser.add_argument("--mock", action="store_true", help="Generate mock transaction data to test the integration and dashboard.")
    parser.add_argument("--all", action="store_true", help="Sync all matching emails, not just unread ones.")
    args = parser.parse_args()

    # Load environment configuration
    pdf_password = args.password or os.environ.get("DIME_PDF_PASSWORD")
    mistral_api_key = os.environ.get("MISTRAL_API_KEY")

    portfolio = get_portfolio_data()
    transactions = get_transactions()

    # Mock mode
    if args.mock:
        print("🧪 Running in MOCK Mode...")
        mock_txs = [
            {
                "source": "Dime",
                "invoice_no": "MOCK-DIME-001",
                "invoice_date": "16/06/2026",
                "order_id": "999991",
                "settlement_date": "18/06/2026",
                "transaction_type": "BUY",
                "ticker": "AAPL",
                "exchange": "XNAS",
                "units": 2.0,
                "unit_price": 185.00,
                "currency": "USD",
                "gross_amount": 370.0,
                "fee": 5.0,
                "withholding_tax": 0.0,
                "total_amount_ccy": 370.0,
                "total_amount_thb": 12950.0
            },
            {
                "source": "WealthX",
                "invoice_no": "MOCK-WX-001",
                "invoice_date": "16/06/2026",
                "order_id": "999992",
                "settlement_date": "18/06/2026",
                "transaction_type": "BUY",
                "ticker": "K-CHANGE-A(A)",
                "name": "K Positive Change Equity Fund",
                "theme": "Global ESG Growth",
                "exchange": None,
                "units": 500.0,
                "unit_price": 13.80,
                "currency": "THB",
                "gross_amount": 6900.0,
                "fee": 10.0,
                "withholding_tax": 0.0,
                "total_amount_ccy": 6910.0,
                "total_amount_thb": 6910.0
            }
        ]
        
        # Merge mock transactions
        transactions.extend(mock_txs)
        portfolio = rebuild_portfolio_from_transactions(portfolio, transactions, new_transactions=mock_txs)
        save_data(portfolio, transactions)
        return

    # Local PDF processing
    if args.pdf:
        if not pdf_password:
            print("❌ Error: PDF decryption password is required. Use --password or set DIME_PDF_PASSWORD in .env")
            sys.exit(1)
        if not mistral_api_key:
            print("❌ Error: MISTRAL_API_KEY is required.")
            sys.exit(1)
            
        temp_decrypted = "manual_decrypted.pdf"
        success = decrypt_pdf(args.pdf, temp_decrypted, pdf_password)
        if success:
            new_txs = ocr_and_extract_transactions(temp_decrypted, mistral_api_key)
            if new_txs:
                filtered_txs = filter_duplicate_transactions(transactions, new_txs)
                if filtered_txs:
                    transactions.extend(filtered_txs)
                    portfolio = rebuild_portfolio_from_transactions(portfolio, transactions, new_transactions=filtered_txs)
                    save_data(portfolio, transactions)
                    generate_tax_report(transactions)
                else:
                    print("😴 No new unique transactions from PDF.")
            else:
                print("⚠️ No transactions parsed from PDF.")
            
            # Clean up
            if os.path.exists(temp_decrypted):
                os.remove(temp_decrypted)
        sys.exit(0)

    # Gmail workflow
    secret_files = glob.glob("client_secret_*.json")
    if not secret_files and not os.path.exists("token.json"):
        print("⚠️ No client_secret_*.json found and no token.json exists.")
        print("💡 To use Gmail REST API, please place your Google Cloud Desktop Client secret JSON file in this directory.")
        print("💡 You can also run manually on a local file: python sync_gmail_dime.py --pdf statement.pdf --password 1234")
        print("💡 Or generate mock data to test: python sync_gmail_dime.py --mock")
        sys.exit(1)

    if not pdf_password:
        print("❌ Error: DIME_PDF_PASSWORD is not set in environment variables.")
        sys.exit(1)
        
    if not mistral_api_key:
        print("❌ Error: MISTRAL_API_KEY is not set in environment variables.")
        sys.exit(1)

    print("🚀 Starting Gmail Sync...")
    new_txs = process_gmail(pdf_password, mistral_api_key, sync_all=args.all)
    
    if new_txs:
        filtered_txs = filter_duplicate_transactions(transactions, new_txs)
        if filtered_txs:
            transactions.extend(filtered_txs)
            portfolio = rebuild_portfolio_from_transactions(portfolio, transactions, new_transactions=filtered_txs)
            save_data(portfolio, transactions)
        else:
            print("😴 No new unique transactions found in Gmail.")
    else:
        print("😴 No new trade confirmations found or processed.")
        
    generate_tax_report(transactions)

if __name__ == "__main__":
    main()
