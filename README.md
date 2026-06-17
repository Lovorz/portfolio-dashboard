# 📊 Personal Investment Portfolio Dashboard

> **เว็บแดชบอร์ดติดตามพอร์ตหุ้นส่วนตัว** สำหรับนักลงทุนไทยที่ลงทุนในหุ้น US, ETF, และกองทุนรวม  
> ผสาน Gmail API, Mistral AI OCR, Obsidian Knowledge Vault, และ AI Risk Advisor เข้าเป็นระบบเดียว

![HTML](https://img.shields.io/badge/HTML-Single%20File-blue?style=flat-square&logo=html5)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![Obsidian](https://img.shields.io/badge/Obsidian-Compatible-7C3AED?style=flat-square&logo=obsidian)

---

## ✨ ฟีเจอร์หลัก (Features)

| ฟีเจอร์ | รายละเอียด |
|--------|-----------|
| 📈 **Live Prices** | ราคาหุ้น US จาก Yahoo Finance แบบ Real-time |
| 💱 **USD/THB** | แสดงมูลค่าทั้ง USD และ THB พร้อมกัน |
| 🤖 **AI Risk Advisor** | แชตกับ AI (Claude/Gemini) วิเคราะห์พอร์ตส่วนตัว |
| 📚 **Obsidian Vault** | คลังความรู้การลงทุนส่วนตัว เชื่อมกับ AI Context |
| 📬 **Gmail Auto-Sync** | ดึงข้อมูลรายการซื้อขายจาก Dime/WealthX Statement PDF อัตโนมัติ |
| 🧠 **Mistral AI OCR** | แปลง PDF Statement ที่มีรหัสผ่านเป็นข้อมูลอัตโนมัติ |
| ⚠️ **Risk Analytics** | Sector Concentration, HHI, Trim Rules, Stop Loss |
| 📋 **Action Plan** | แผนการจัดพอร์ตตาม FOMC Scenarios |
| 👁️ **Censor Mode** | ปิดบังตัวเลขสำหรับ Screenshot |
| 🔄 **Auto-refresh** | อัปเดตราคาทุก 60 วินาที |

---

## 🗂️ โครงสร้างโปรเจกต์ (Project Structure)

```
portfolio/
├── portfolio.html                  ← แดชบอร์ดหลัก (ทุกอย่างอยู่ในไฟล์นี้)
├── server.py                       ← Local Python server + Obsidian Sync API
├── sync_gmail_dime.py              ← Gmail API + Mistral AI PDF OCR pipeline
├── build_obsidian_knowledge.py     ← สร้าง Obsidian Vault จาก PDF/Word
├── portfolio_data.example.json     ← Template ข้อมูลพอร์ต (copy → portfolio_data.json)
├── .env.example                    ← Template API keys (copy → .env)
├── documents/                      ← โฟลเดอร์ใส่ PDF Statement, Word ไฟล์
└── Investment_guidelines/          ← Obsidian Vault (สร้างอัตโนมัติ)
```

> ⚠️ ไฟล์ `portfolio_data.json`, `.env`, `token.json`, และ `documents/` ถูกซ่อนด้วย `.gitignore` จะไม่ถูก push ขึ้น GitHub

---

## 🚀 เริ่มต้นใช้งาน (Quick Start)

### ขั้นตอนที่ 1 — Clone โปรเจกต์

```bash
git clone https://github.com/YOUR_USERNAME/portfolio.git
cd portfolio
```

### ขั้นตอนที่ 2 — ติดตั้ง Python dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client mistralai python-dotenv python-docx PyMuPDF openpyxl
```

### ขั้นตอนที่ 3 — สร้างไฟล์ข้อมูลของคุณ

```bash
# Copy template และแก้ไขใส่ข้อมูลพอร์ตของคุณ
cp portfolio_data.example.json portfolio_data.json

# Copy template API keys
cp .env.example .env
```

แก้ไข `.env`:
```env
DIME_PDF_PASSWORD=your_thai_id_or_dob      # รหัสเปิด PDF Statement ของ Dime
MISTRAL_API_KEY=your_mistral_api_key       # จาก console.mistral.ai
```

### ขั้นตอนที่ 4 — รัน Local Server

```bash
python3 server.py
```

เปิด browser ไปที่ `http://localhost:8080`

---

## 🔑 การตั้งค่า API Keys แบบละเอียด

### 1. 🤖 Mistral AI (สำหรับ OCR PDF Statement)

Mistral AI ใช้อ่าน PDF Statement ของ Dime/WealthX ที่มีรหัสผ่าน และแปลงเป็นข้อมูลรายการซื้อขาย

**ขั้นตอนขอ Mistral API Key:**
1. ไปที่ [https://console.mistral.ai](https://console.mistral.ai)
2. สมัครบัญชีด้วย Google หรืออีเมล
3. ไปที่ **API Keys** → **Create new key**
4. Copy key และใส่ใน `.env`:
   ```
   MISTRAL_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. Mistral มี Free Tier ที่ใช้งานได้ (โมเดล `mistral-small-latest`)

---

### 2. 📬 Gmail API (สำหรับดึง Statement อัตโนมัติ)

Gmail API ใช้ค้นหาและดาวน์โหลด PDF Statement ที่ส่งมาทาง Email จาก Dime และ WealthX

**ขั้นตอนตั้งค่า Google Cloud Console:**

1. ไปที่ [https://console.cloud.google.com](https://console.cloud.google.com)
2. สร้าง **New Project** ตั้งชื่อ เช่น `portfolio-dashboard`
3. ไปที่ **APIs & Services** → **Enable APIs**
   - ค้นหา `Gmail API` แล้วกด Enable
4. ไปที่ **APIs & Services** → **Credentials**
5. กด **Create Credentials** → **OAuth 2.0 Client IDs**
   - Application type: **Desktop App**
   - ตั้งชื่อ เช่น `Portfolio Sync`
6. กด **Download JSON** → บันทึกเป็น `client_secret_*.json` ในโฟลเดอร์โปรเจกต์

**ขั้นตอน OAuth Consent Screen:**
1. ไปที่ **OAuth consent screen** → External → Create
2. ใส่ชื่อ App, อีเมลของคุณ
3. ไปที่ **Scopes** → Add scope → เลือก `gmail.readonly`
4. ไปที่ **Test users** → เพิ่มอีเมล Gmail ของคุณ

**รันครั้งแรก (ต้อง Login):**
```bash
python3 sync_gmail_dime.py
```
> จะเปิด browser ให้ Login Google อัตโนมัติ — หลังจากนั้น `token.json` จะถูกสร้างขึ้น ไม่ต้อง login ซ้ำอีก

---

### 3. 🧠 AI Chat — Claude หรือ Gemini (สำหรับ Risk Advisor)

ระบบรองรับทั้งสองค่าย เลือกใช้ได้ตามต้องการ:

**Claude (Anthropic):**
1. ไปที่ [https://console.anthropic.com](https://console.anthropic.com)
2. สมัครบัญชีและเติมเครดิต (เริ่มต้นประมาณ $5)
3. ไปที่ **API Keys** → **Create Key**
4. ใส่ key ใน Dashboard → กล่อง "API Key Settings" → Claude tab

**Gemini (Google):**
1. ไปที่ [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. กด **Create API Key** (ฟรี ไม่ต้องเสียเงิน)
3. ใส่ key ใน Dashboard → กล่อง "API Key Settings" → Gemini tab

> 💡 Key ทั้งหมดถูกบันทึกใน `localStorage` ของ browser เท่านั้น ไม่มีการส่งออก server

---

### 4. 📰 FMP API (สำหรับ Stock News — Optional)

Financial Modeling Prep ให้ข่าวหุ้น US แบบ Real-time

1. ไปที่ [https://financialmodelingprep.com](https://financialmodelingprep.com)
2. สมัครบัญชี → Free plan ให้ 250 calls/day
3. Copy API Key → ใส่ใน Dashboard แท็บ "ข่าวสาร" → ⚙️ FMP Key

---

## 📚 การตั้งค่า Obsidian Knowledge Vault

Obsidian Vault คือ "สมองที่สอง" ที่เก็บคู่มือการลงทุน บทความวิเคราะห์ และ clip จาก Facebook  
ระบบจะแปลงเอกสารเหล่านี้เป็น AI Context โดยอัตโนมัติ

### ขั้นตอนที่ 1 — ใส่เอกสารคู่มือ

สร้างโฟลเดอร์ `documents/` และใส่ไฟล์ต่างๆ:
```
documents/
├── คู่มือการลงทุน.pdf
├── วิเคราะห์หุ้น.docx
└── ภาพ_Infographic.jpg
```

รองรับ: `.pdf`, `.docx`, `.xlsx`, `.jpg`, `.jpeg`

### ขั้นตอนที่ 2 — สร้าง Vault

```bash
python3 build_obsidian_knowledge.py
```

ระบบจะสร้างโฟลเดอร์ `Investment_guidelines/` อัตโนมัติ พร้อมไฟล์ Markdown ที่อ่านได้ใน Obsidian

### ขั้นตอนที่ 3 — เปิดใน Obsidian (Optional แต่แนะนำ)

1. ดาวน์โหลด [Obsidian](https://obsidian.md) (ฟรี)
2. กด **Open folder as vault** → เลือกโฟลเดอร์ `Investment_guidelines/`
3. เปิด Graph View เพื่อดูความเชื่อมโยงระหว่างเอกสาร

### ขั้นตอนที่ 4 — เพิ่ม Knowledge Card ผ่าน Dashboard

ในแท็บ "กลยุทธ์ & Watchlist":
1. กดปุ่ม **"นำเข้าการ์ดความรู้"**
2. ใส่ชื่อ, หมวดหมู่, สัญลักษณ์หุ้น (ticker), และข้อความ
3. แนบภาพ Screenshot ได้โดยตรง (วาง `Ctrl+V` หรือเลือกไฟล์)
4. กด **"บันทึก"** — ระบบจะสร้าง Obsidian Note และอัปเดต AI Context อัตโนมัติ

---

## 📬 การ Sync Gmail Statement (Dime & WealthX)

```bash
python3 sync_gmail_dime.py
```

สคริปต์จะ:
1. ค้นหา Email จาก Dime และ WealthX ที่มี PDF แนบ
2. ดาวน์โหลดและถอดรหัส PDF ด้วย password จาก `.env`
3. ส่ง PDF ไปยัง Mistral AI เพื่อ OCR และวิเคราะห์รายการ
4. บันทึกผลลัพธ์ใน `transactions.json` และ `portfolio_data.json`
5. ระบบ Deduplication ป้องกันรายการซ้ำโดยอัตโนมัติ

> 📌 รันทุกสิ้นเดือนเมื่อได้รับ Statement ใหม่

---

## ⚙️ การแก้ไขข้อมูลพอร์ตด้วยตนเอง

เปิดไฟล์ `portfolio_data.json` แล้วแก้ข้อมูลส่วนต่างๆ:

### โครงสร้างข้อมูลหลัก

```json
{
  "investor_profile": {
    "name": "ชื่อของคุณ",
    "age": 26,
    "income": 16000,
    "expense": 12000,
    "goal": "เป้าหมายการลงทุน"
  },
  "cash": {
    "now": 13000,       ← เงินสดปัจจุบัน (THB)
    "target": 72000     ← เป้าหมาย Cash Buffer (THB)
  },
  "wealthx_funds": [...],   ← กองทุน WealthX/ไทย
  "dime_assets": [...],     ← หุ้น/ETF ใน Dime App
  "ideas": [...],           ← Watchlist
  "trim_rules": [...],      ← กฎขาย (Take Profit)
  "review_rules": [...]     ← กฎตัดขาดทุน (Stop Loss)
}
```

ดูตัวอย่างเต็มได้ใน `portfolio_data.example.json`

---

## 🛠️ Troubleshooting

| ปัญหา | วิธีแก้ |
|-------|--------|
| หน้าขาว / ไม่โหลดข้อมูล | รัน `python3 server.py` แล้วเปิดจาก `localhost:8080` |
| ราคาหุ้นไม่อัปเดต | ปิด Browser Shield / Ad-blocker ชั่วคราว |
| Gmail ไม่ยอม login | ลบ `token.json` แล้วรัน sync script ใหม่ |
| PDF OCR ผิดพลาด | ตรวจสอบ `DIME_PDF_PASSWORD` ใน `.env` ให้ถูกต้อง |
| Obsidian ไม่แสดงไฟล์ใหม่ | รัน `python3 build_obsidian_knowledge.py` ใหม่ |
| AI ไม่ตอบ | ตรวจสอบ API Key ใน Dashboard → API Key Settings |

---

## 🔒 ความปลอดภัย (Security Notes)

- `.env`, `token.json`, `portfolio_data.json` และ `documents/` **ไม่ถูก push ขึ้น GitHub** (ป้องกันโดย `.gitignore`)
- AI API Keys ถูกเก็บใน **Browser localStorage** เท่านั้น
- Gmail token ให้สิทธิ์แค่ **read-only** ไม่สามารถส่ง/ลบ email ได้
- ใช้ภายใน Local Network เท่านั้น ไม่แนะนำ deploy บน Public Server โดยไม่ใส่ Authentication

---

## 📄 License

MIT — ใช้ได้ฟรี แก้ได้ แจกจ่ายได้ ไม่ต้องขออนุญาต

---

*สร้างด้วย Claude / Antigravity · สำหรับนักลงทุนไทยที่ลงทุนในหุ้นสหรัฐและกองทุนรวม*
