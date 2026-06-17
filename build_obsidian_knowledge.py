import os
import re
import json
import requests
import docx
import pypdf

# Define list of files and their IDs in Google Drive
DRIVE_FILES = [
    {"id": "13H79WQqrCtoY-A6VRJ3i_vnmpp5Gfkg9", "name": "001_การลงทุน_101_by_EarthhEvans.pdf", "cat": "Basics"},
    {"id": "1PtQ-7AyV9yKvVroLHqHFqbLb5ZuPBpdD", "name": "002_อ่านงบการเงิน101.docx", "cat": "Fundamentals"},
    {"id": "1JfoRVPuvRB3y_Ycls9TGFYXcwQ42yrTB", "name": "003_ValueInvesting_Damodaran_Thai_by_EarthhEvans_1.pdf", "cat": "Valuation"},
    {"id": "11qDkJAmhGmjxrxreA_dfxW1wyC3_65rf", "name": "004_Macro Playbook for Stock Pickers - Earthh Evans.docx", "cat": "Macro"},
    {"id": "1TK0QTXZZRn7gH_UrtKdPRFiMIkC-k4yI", "name": "006_Technical_101_for_Thinkers_RELOADED.pdf", "cat": "Technicals"},
    {"id": "1J3veZHM8NBD6FY6vlij7h-JDF8AtinTH", "name": "007_Asset_Allocation_Master_Playbook_Final_Distribution_by_Earthh_Evans.pdf", "cat": "Allocation"},
    {"id": "15GzPjP22LbNOLazeeppus1Bnk_5VlM08", "name": "008_Long_Call_Long_Put_Complete_Guide_EarthhEvans.docx", "cat": "Options"},
    {"id": "1cMWvaMOJGCAIudjxjrF96hgJryaJwkd2", "name": "09_Risk_Management_Deep_Dive.pdf", "cat": "Risk"},
    {"id": "1Caxmx3N8ZFPwFUF8UTVmVv8OIC1lwEUo", "name": "Portfolio_Risk_Architect_Skill.pdf", "cat": "Risk"},
    {"id": "1BBLXvJWXovchSMOYSrXlKIlnVb2ytgWD", "name": "สอน ReverseDCF_TerminalAnchored.pdf", "cat": "Valuation"},
    {"id": "1AZ5zPUsXTsojvQR5ymLbJ7fcf1MXz9GT", "name": "reverse_dcf_Template.xlsx", "cat": "Templates"},
    {"id": "1BWIKfhplrniQO5D0RHDIS3rIp10yiW17", "name": "ซื้อทองแบบไหนดี.pdf", "cat": "Alternative"},
    {"id": "14UBbk1YnCa7j-o_p3D-e_fX11q4CV_id", "name": "01_WealthRoadmap_FULL.docx", "cat": "Basics"},
    {"id": "1qvgtQO_dsaJDQA5Gz2rmPE_lDUR0t38t", "name": "Fundamental_Growth.pdf", "cat": "Fundamentals"},
    {"id": "1HQD3_5N1VrJZuqE4T_K661D8k3C3hz0Q", "name": "โครงสร้างตลาดหุ้นเมกา.docx", "cat": "Markets"},
    {"id": "1WEWPxAPKVFDQ4ViyKgxIz14C0hH03pAB", "name": "Semiconductor_Value_Chain.pdf", "cat": "Industry Analysis"},
    {"id": "1SNf_VnfY9GhFOrtMh6nrhwZcdfcir65O", "name": "06_เลือกหุ้นผ่านดัชนี.docx", "cat": "Fundamentals"},
    {"id": "1Mpqu85ZXXGDDpA174qeCXX62IoAGvltZ", "name": "03_คู่มือวิเคราะห์หุ้นปันผล_Thesis_Full_Edition_polished.docx", "cat": "Valuation"},
    {"id": "1xxrmkLsYXuIloV8kRTBT-QMGMCxr-NT7", "name": "04_Fundamental Checklist101.docx", "cat": "Fundamentals"},
    {"id": "1wjaFdDpf7nc5Z0oItYufOOEGpTdGqZeH", "name": "07_หุ้นพื้นฐานดี101.docx", "cat": "Fundamentals"},
    {"id": "1D9UK8Us12VcUh4zjiUttIMfHpSH8BIye", "name": "หุ้นโลก และ ทองคำ.pdf", "cat": "Alternative"},
    {"id": "1mI1zWKqbjp4CuoCI4Ct3CHTSldaAicWR", "name": "Timeline เมื่ออยากเริ่มลงทุน-01.jpeg", "cat": "Resources"},
    {"id": "1YwsrguzCaaUF0WtQsyJFxb29iXOnBnni", "name": "ระบบจัดพอร์ต.jpeg", "cat": "Resources"}
]

# Set up paths
DOCUMENTS_DIR = "documents"
OBSIDIAN_DIR = "Investment_guidelines"

os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(OBSIDIAN_DIR, exist_ok=True)

# Helper for large Google Drive files download
def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    response = session.get(URL, params={'id': file_id}, stream=True)
    token = get_confirm_token(response)
    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)
    save_response_content(response, destination)

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

def clean_text(text):
    # Remove excessive empty lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Remove weird null characters
    text = text.replace('\u0000', '')
    return text.strip()

# Main process loop
principles_extracted = []

print("🚀 Starting Investment Guide Pipeline to build Obsidian Knowledge Base & AI Context...")
print(f"Directory: {os.getcwd()}")

for i, item in enumerate(DRIVE_FILES, 1):
    file_id = item["id"]
    filename = item["name"]
    category = item["cat"]
    base_name, ext = os.path.splitext(filename)
    
    print(f"\n[{i}/{len(DRIVE_FILES)}] Processing: {filename}...")
    local_path = os.path.join(DOCUMENTS_DIR, filename)
    
    # 1. Download
    if not os.path.exists(local_path):
        print(f"   Downloading from Google Drive (ID: {file_id})...")
        try:
            download_file_from_google_drive(file_id, local_path)
            print(f"   Saved to {local_path} (Size: {os.path.getsize(local_path)} bytes)")
        except Exception as e:
            print(f"   ⚠️ Failed to download: {e}")
            continue
    else:
        print(f"   Found cached file at {local_path}")

    # Create category subfolder in Obsidian Vault
    cat_dir = os.path.join(OBSIDIAN_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    md_filename = f"{base_name}.md"
    md_path = os.path.join(cat_dir, md_filename)

    # 2. Text Extraction
    text_content = ""
    if ext.lower() == '.pdf':
        print("   Extracting text from PDF...")
        try:
            reader = pypdf.PdfReader(local_path)
            pages = []
            for p_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(f"## Page {p_idx + 1}\n\n{text}")
            text_content = "\n\n".join(pages)
        except Exception as e:
            print(f"   ⚠️ PDF extraction error: {e}")
    elif ext.lower() == '.docx':
        print("   Extracting text from Word Document...")
        try:
            doc = docx.Document(local_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text_content = "\n\n".join(paragraphs)
        except Exception as e:
            print(f"   ⚠️ Word extraction error: {e}")
    elif ext.lower() in ['.xlsx', '.xls']:
        text_content = f"Template file for calculation. Excel template sheet available in documents/{filename}."
    elif ext.lower() in ['.jpeg', '.jpg', '.png']:
        text_content = f"Visual resource image. Available at documents/{filename}."
    else:
        text_content = "Raw text content placeholder."

    text_content = clean_text(text_content)

    # 3. Create Obsidian Markdown Notes
    # Construct obsidian backlinks to other guides
    backlinks = []
    for other in DRIVE_FILES:
        if other["name"] != filename and other["cat"] == category:
            other_base = os.path.splitext(other["name"])[0]
            backlinks.append(f"[[{other_base}]]")
    
    backlink_section = ""
    if backlinks:
        backlink_section = f"\n\n### 🔗 Related in {category}\n" + " · ".join(backlinks)

    # Add Obsidian metadata YAML frontmatter
    md_body = f"""---
tags:
  - investing/{category.lower().replace(' ', '-')}
  - earthh-evans/playbook
source_drive_id: {file_id}
category: {category}
---

# 📖 {base_name.replace('_', ' ')}

{text_content}
{backlink_section}
"""
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_body)
    print(f"   ✓ Created Obsidian Note: {md_path}")

    # Core principles extracted dynamically in the folder walk step below
    pass

# 4. Scan the local Investment_guidelines vault folder for ALL Markdown notes
principles_extracted = []
print("\n🔍 Scanning local vault folder for Markdown files to update AI Principles...")

# Traverse directory recursively
for root, dirs, files in os.walk(OBSIDIAN_DIR):
    for file in files:
        if file.endswith('.md') and file != "Index.md":
            filepath = os.path.join(root, file)
            # Determine category based on subdirectory path relative to vault root
            rel_dir = os.path.relpath(root, OBSIDIAN_DIR)
            category = "Custom" if rel_dir == "." else rel_dir
            base_name = os.path.splitext(file)[0]
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for YAML frontmatter
                ticker_trigger = ""
                body = content
                
                # Extract frontmatter
                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
                if frontmatter_match:
                    yaml_text = frontmatter_match.group(1)
                    body = frontmatter_match.group(2)
                    
                    # Read category from frontmatter
                    cat_match = re.search(r'^category:\s*(.*?)$', yaml_text, re.MULTILINE)
                    if cat_match:
                        category = cat_match.group(1).strip()
                        
                    # Read ticker from frontmatter
                    ticker_match = re.search(r'^ticker:\s*(.*?)$', yaml_text, re.MULTILINE)
                    if ticker_match:
                        ticker_trigger = ticker_match.group(1).strip()
                
                # Fallback ticker trigger if notes start with digit prefixes
                if not ticker_trigger and base_name.startswith('0'):
                    ticker_trigger = base_name.split('_')[0]
                
                # Clean markdown characters for the AI summary
                body_clean = re.sub(r'#+\s+.*?\n', '', body) # remove heading tags
                body_clean = re.sub(r'\[\[(.*?)\]\]', r'\1', body_clean) # replace [[backlinks]] with plain text
                
                lines = [line.strip() for line in body_clean.split('\n') if len(line.strip()) > 30]
                summary = " ".join(lines[:4])
                if len(summary) > 400:
                    summary = summary[:400] + "..."
                elif not summary:
                    summary = body_clean[:400].strip() + "..."
                
                principles_extracted.append({
                    "ticker_trigger": ticker_trigger,
                    "name": base_name,
                    "category": category,
                    "summary": clean_text(summary)
                })
                print(f"   ✓ Indexed: [{category}] {base_name} (Ticker: {ticker_trigger})")
            except Exception as e:
                print(f"   ⚠️ Failed to read/index {file}: {e}")

# 5. Build Obsidian Index.md (Welcome map) dynamically from scanned files
index_path = os.path.join(OBSIDIAN_DIR, "Index.md")
index_body = """# 📚 Earthh Evans - Investment Playbook Vault

ยินดีต้อนรับสู่คลังความรู้การลงทุนถาวร (Second Brain) ที่จัดทำโดย **Senior Risk Manager: Earthh Evans** 
คุณสามารถนำโฟลเดอร์ `Investment_guidelines` นี้ไปเปิดในแอปพลิเคชัน **Obsidian** เพื่อเปิดอ่านการ์ดความรู้และคลิกเชื่อมโยงข้อมูลหากันผ่าน Link `[[การ์ดความรู้]]` ได้ทันที

## 🗂 สารบัญแยกตามหัวข้อการลงทุน

"""

categories_grouped = {}
for p in principles_extracted:
    cat = p["category"]
    if cat not in categories_grouped:
        categories_grouped[cat] = []
    categories_grouped[cat].append(p["name"])

for cat in sorted(categories_grouped.keys()):
    index_body += f"\n### 📂 {cat}\n"
    for note in sorted(categories_grouped[cat]):
        index_body += f"* [[{note}]]\n"

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(index_body)
print(f"\n✓ Generated Obsidian Welcome Index: {index_path}")

# 6. Save JSON Principles for AI Risk Manager Widget
principles_path = "earthh_evans_principles.json"
with open(principles_path, 'w', encoding='utf-8') as f:
    json.dump(principles_extracted, f, ensure_ascii=False, indent=2)
print(f"✓ Distilled AI Principles saved to: {principles_path}")
print("\n🎉 Knowledge Base Pipeline Completed successfully!")
