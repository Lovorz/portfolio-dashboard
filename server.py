import os
import sys
import json
import base64
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8080
DOCUMENTS_DIR = "documents"
OBSIDIAN_DIR = "Investment_guidelines"

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

    def do_POST(self):
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
