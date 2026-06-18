import os
import sys
import re
import json
import shutil
import base64
import subprocess
import urllib.request
from urllib.parse import urlparse, parse_qs

# Resolve the Claude Code CLI once (PATH inside the server may differ from the shell).
CLAUDE_BIN = shutil.which('claude') or os.path.expanduser('~/.local/bin/claude')
from http.server import SimpleHTTPRequestHandler, HTTPServer
from concurrent.futures import ThreadPoolExecutor

PORT = 8080
DOCUMENTS_DIR = "documents"
OBSIDIAN_DIR = "Investment_guidelines"

def fetch_single_quote(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return {
                "symbol": meta.get('symbol', symbol),
                "regularMarketPrice": meta.get('regularMarketPrice', 0)
            }
    except Exception as e:
        print(f"Error fetching chart for {symbol}: {e}")
        return None

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS headers for development/local use
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Prevent browser caching of HTML/JSON assets during local runs
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/yahoo_finance':
            query_params = parse_qs(parsed_url.query)
            symbols_str = query_params.get('symbols', [''])[0]
            if not symbols_str:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing symbols parameter"}).encode('utf-8'))
                return
            
            symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
            
            results = []
            # Fetch concurrently using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = executor.map(fetch_single_quote, symbols)
                for res in futures:
                    if res is not None:
                        results.append(res)
            
            response_data = {
                "quoteResponse": {
                    "result": results
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        elif parsed_url.path == '/api/fx_rate':
            query_url = "https://open.er-api.com/v6/latest/USD"
            try:
                req = urllib.request.Request(
                    query_url, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/fmp_news':
            query_params = parse_qs(parsed_url.query)
            ticker = query_params.get('ticker', [''])[0].strip()
            apikey = query_params.get('apikey', [''])[0].strip()
            if not ticker or not apikey:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing ticker or apikey parameter"}).encode('utf-8'))
                return
            
            # FMP free tier exposes /stable/fmp-articles (general feed), NOT /api/v3/stock_news (paywalled).
            # Mirror the RichieGem approach: page through the feed and filter by ticker client-side.
            ticker_up = ticker.upper()
            def _clean_html(raw):
                return re.sub(r'<[^>]+>', '', raw or '').strip()
            try:
                results = []
                for page in range(3):  # 3 pages x 50 = up to 150 recent articles
                    page_url = (f"https://financialmodelingprep.com/stable/fmp-articles"
                                f"?page={page}&limit=50&apikey={urllib.parse.quote(apikey)}")
                    req = urllib.request.Request(page_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        articles = json.loads(response.read())
                    if not isinstance(articles, list) or not articles:
                        break
                    for item in articles:
                        tickers_field = (item.get('tickers') or '')
                        title = item.get('title') or ''
                        if ticker_up in tickers_field.upper() or ticker_up in title.upper():
                            related = [t.split(':')[-1].strip().upper()
                                       for t in tickers_field.split(',') if t.strip()]
                            results.append({
                                'title': title,
                                'publishedDate': item.get('date', ''),
                                'site': item.get('site') or item.get('publisher') or 'FMP',
                                'text': _clean_html(item.get('content', ''))[:600],
                                'url': item.get('link', '#'),
                                'relatedTickers': related
                            })
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        # Fallback to SimpleHTTPRequestHandler to serve local files
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/cli_analyze':
            # Run analysis through the local Claude Code CLI (uses the user's
            # subscription — no API key in the browser, no Gemini rate limits).
            try:
                length = int(self.headers.get('Content-Length', 0))
                payload = json.loads(self.rfile.read(length) or b'{}')
            except Exception:
                payload = {}
            prompt = (payload.get('prompt') or '').strip()
            system = (payload.get('system') or '').strip()
            fast = bool(payload.get('fast', False))

            if not prompt:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing prompt"}).encode('utf-8'))
                return
            if not (CLAUDE_BIN and os.path.exists(CLAUDE_BIN)):
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Claude CLI not found on server"}).encode('utf-8'))
                return

            cmd = [CLAUDE_BIN, '-p', '--output-format', 'text',
                   '--model', 'haiku' if fast else 'sonnet',
                   '--disallowedTools', 'Bash', 'Edit', 'Write', 'Read', 'WebFetch', 'WebSearch', 'Task']
            if system:
                cmd += ['--append-system-prompt', system]
            try:
                result = subprocess.run(cmd, input=prompt, capture_output=True,
                                        text=True, timeout=180)
                if result.returncode != 0:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": (result.stderr or 'CLI error').strip()[:500]}).encode('utf-8'))
                    return
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"text": result.stdout.strip()}).encode('utf-8'))
            except subprocess.TimeoutExpired:
                self.send_response(504)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Claude CLI timed out"}).encode('utf-8'))
            return

        if self.path == '/api/sync_note':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                title = data.get('title', 'Untitled').strip()
                # Replace whitespace and invalid chars with underscores for safe filenames
                safe_title = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in title)
                safe_title = safe_title.replace(' ', '_')
                
                category = data.get('category', 'Custom').strip()
                ticker = data.get('ticker', '').strip().upper()
                content = data.get('content', '').strip()
                image_data = data.get('image', '')
                image_name = data.get('image_name', '')
                
                # Ensure category directory exists
                cat_dir = os.path.join(OBSIDIAN_DIR, category)
                os.makedirs(cat_dir, exist_ok=True)
                
                md_path = os.path.join(cat_dir, f"{safe_title}.md")
                
                image_ref = ""
                # Parse base64 encoded image data if provided
                if image_data and ',' in image_data:
                    header, encoded = image_data.split(',', 1)
                    file_ext = "png"
                    if "jpeg" in header or "jpg" in header:
                        file_ext = "jpg"
                    elif "gif" in header:
                        file_ext = "gif"
                    
                    if not image_name:
                        image_name = f"image_{safe_title}.{file_ext}"
                    else:
                        # Extract basename and clean it
                        clean_img_name = "".join(c if c.isalnum() or c in ('.', '-', '_') else '_' for c in image_name)
                        image_name = os.path.splitext(clean_img_name)[0] + f".{file_ext}"
                        
                    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
                    img_path = os.path.join(DOCUMENTS_DIR, image_name)
                    
                    with open(img_path, 'wb') as img_f:
                        img_f.write(base64.b64decode(encoded))
                    
                    # Store link formatted for local image loading in Markdown note
                    image_ref = f"\n\n![Reference Screenshot]({os.path.join('documents', image_name)})\n"
                    print(f"✓ Saved image: {img_path}")
                
                # Write frontmatter and note body
                yaml_header = f"""---
tags:
  - earthh-evans/custom-clip
category: {category}
"""
                if ticker:
                    yaml_header += f"ticker: {ticker}\n"
                yaml_header += "---\n\n"
                
                md_body = yaml_header + f"# 📖 {title}\n\n{content}{image_ref}"
                
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_body)
                print(f"✓ Created/Updated Obsidian note: {md_path}")
                
                # Run the dynamic scanner pipeline script to compile new principles JSON
                print("🔄 Re-indexing vault notes database...")
                result = subprocess.run([sys.executable, "build_obsidian_knowledge.py"], capture_output=True, text=True)
                print("✓ Build Script output:", result.stdout.strip())
                
                # Return success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_body = json.dumps({
                    "status": "success", 
                    "message": f"สร้างการ์ดความรู้ [[{title}]] ในหมวดหมู่ {category} เรียบร้อยแล้ว!"
                })
                self.wfile.write(response_body.encode('utf-8'))
                
            except Exception as e:
                print("❌ Error processing sync API:", e)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_body = json.dumps({"status": "error", "message": str(e)})
                self.wfile.write(response_body.encode('utf-8'))
        else:
            super().do_POST()

if __name__ == '__main__':
    # Start web server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
    print(f"🚀 Custom Portfolio Server running on port {PORT} with Sync API support...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
