# ⚒️ CurricuForge
### AI-Powered Curriculum Generation Platform
> Built with IBM Granite 3.3 2B · Ollama · Streamlit · ReportLab

---

## What is CurricuForge?

CurricuForge is an intelligent curriculum design platform that automatically generates complete, semester-wise educational syllabi using AI. Simply enter a skill domain, education level, and a few preferences — and get a fully structured curriculum in seconds.

All AI processing runs **entirely offline** on your local machine via Ollama. No internet, no API keys, no subscription costs.

---

## Features

- AI-generated semester-wise curriculum with course names, codes, credits, and topics
- Supports Diploma, BTech, Master's Degree, and Professional Certification levels
- Downloadable PDF syllabus with professional formatting
- JSON export in Raw, LMS-Ready, and Summary formats
- Fully offline — powered by IBM Granite 3.3 2B via Ollama
- Clean, modern UI built with Streamlit

---

## Project Structure

```
Project Panchajanya/
├── ai_engine.py          # AI core — Ollama integration, prompt engineering, JSON extraction
├── app.py                # Streamlit frontend + UI
├── pdf_generator.py      # ReportLab PDF generation
├── json_exporter.py      # JSON export (Raw, LMS-Ready, Summary)
├── test_ai_engine.py     # Unit tests for AI engine (38 tests)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Setup Instructions

### Step 1 — Install Ollama
Download from: https://ollama.com/download

### Step 2 — Pull IBM Granite Model
```bash
ollama pull granite3.3:2b
```

### Step 3 — Start Ollama
```bash
ollama serve
```

### Step 4 — Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/curricuforge.git
cd curricuforge
```

### Step 5 — Create Virtual Environment
```bash
python3 -m venv panchajanya_env
source panchajanya_env/bin/activate
```

### Step 6 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 7 — Run the App
```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

---

## How to Use

1. Enter a **Skill or Subject Domain** (e.g. Machine Learning)
2. Select an **Education Level** (Diploma / BTech / Master's / Certification)
3. Set **Number of Semesters** (2–8)
4. Set **Weekly Study Hours** (10–30)
5. Enter an **Industry Focus** (e.g. AI, FinTech, Healthcare)
6. Click **Generate Curriculum**
7. Download the PDF or JSON export

---

## Technology Stack

| Layer | Technology |
|---|---|
| AI Model | IBM Granite 3.3 2B |
| Local AI Runtime | Ollama |
| Backend + Frontend | Streamlit |
| PDF Generation | ReportLab |
| Language | Python 3.13 |

---

## Running Tests

```bash
python test_ai_engine.py
```

Expected output: **38/38 tests passed**

---

## Team

Built for **Project Panchajanya**

- **AI Engine Developer** — Ollama integration, prompt engineering, JSON extraction, retry logic
- **Frontend Developer** — Streamlit UI, PDF download, curriculum display