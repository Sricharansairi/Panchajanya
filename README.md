# ⚒️ CurricuForge
### AI-Powered Curriculum Generation Platform
> Built with Llama 3.3 70B · Groq · OpenRouter · Streamlit · ReportLab

[🚀 View Live App](https://curricuforge-panchajanya.streamlit.app)

---

## What is CurricuForge?

CurricuForge is an intelligent curriculum design platform that automatically generates complete, semester-wise educational syllabi using AI. Simply enter a skill domain, education level, and a few preferences — and get a fully structured curriculum in seconds.

It leverages the power of **Llama 3.3 70B** via lightning-fast Groq APIs (with OpenRouter fallback) to generate professional, industry-ready educational content.

---

## Features

- **AI-Generated Syllabi**: Semester-wise curriculum with course names, codes, credits, and topics
- **Targeted Modes**: Choose between *Fresher Mode* (strong academic foundation) or *Professional Mode* (industry-focused, hands-on)
- **Skill Gap Analysis**: Input current skills to focus the curriculum only on what you need to learn
- **Multi-Language Support**: Generate curricula in English, Hindi, Telugu, Tamil, Kannada, Spanish, French, and German
- **AI Study Planner**: Automatically generate weekly study schedules
- **Job Role Mapping**: Map educational curricula to real industry job roles and salary expectations
- **Automated Email Reminders**: Get notified 3 days before, 1 day before, and on the start day of each semester
- **Analytics Dashboard**: Visual charts and insights of the curriculum credits, hours, and required skills
- **Interactive Chat**: Ask doubts and discuss the generated curriculum directly with the AI
- **Export Options**: Downloadable PDF syllabus with professional formatting or JSON (Raw, LMS-Ready, Summary)
- **Clean, Modern UI**: Built with Streamlit for a fast and responsive experience

---

## Project Structure

```text
Project Panchajanya/
├── ai_engine.py          # AI core — Groq/OpenRouter integration, prompt engineering
├── app.py                # Streamlit frontend, UI, Analytics, Chat, and integrations
├── reminder_scheduler.py # Background scheduler for automated semester email reminders
├── pdf_generator.py      # ReportLab PDF generation for Curriculum, Study Plan, etc.
├── json_exporter.py      # JSON export (Raw, LMS-Ready, Summary)
├── test_ai_engine.py     # Unit tests for AI engine
├── requirements.txt      # Python dependencies
├── .env                  # API keys and environment variables (Not tracked in git)
├── .env.example          # Example environment variable file
└── README.md             # This file
```

---

## Setup Instructions

### Step 1 — Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/curricuforge.git
cd curricuforge
```

### Step 2 — Create Virtual Environment
```bash
python3 -m venv panchajanya_env
source panchajanya_env/bin/activate  # On Windows: panchajanya_env\Scripts\activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure API Keys
Copy the example environment file and insert your API keys:
```bash
cp .env.example .env
```
Open `.env` and add your **Groq API Key** (`GROQ_API_KEY`) and/or **OpenRouter API Key** (`OPENROUTER_API_KEY`). For the reminder system to work, also configure the SMTP email credentials as needed.

### Step 5 — Run the App
```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

Or try the live deployed version: **[https://curricuforge-panchajanya.streamlit.app](https://curricuforge-panchajanya.streamlit.app)**

---

## How to Use

1. Enter a **Skill or Subject Domain** (e.g. Machine Learning)
2. Select an **Education Level** (Diploma / BTech / Master's / Certification)
3. Set **Number of Semesters** and **Weekly Study Hours**
4. (Optional) Toggle **Skill Gap Analysis** and enter your current skills
5. Select your preferred **Output Language**
6. Click **Generate ✨**
7. Once generated, explore the **Analytics Dashboard**, generate a **Study Plan**, or map the curriculum to **Job Roles**
8. Save it to **History**, ask the AI doubts, or download the **PDF/JSON** export
9. (Optional) Setup automated semester reminders via the UI.

---

## Technology Stack

| Layer | Technology |
|---|---|
| AI Model | Llama 3.3 70B |
| API Providers | Groq (Primary), OpenRouter (Fallback) |
| Backend + Frontend | Streamlit |
| PDF Generation | ReportLab |
| Task Scheduling | schedule (Python) |
| Language | Python 3.13 |

---

## Running Tests

```bash
python test_ai_engine.py
```

---

## Team

Built for **Project Panchajanya**

- **AI Engine Developer** — LLM integration, prompt engineering, JSON extraction, retry logic
- **Frontend Developer** — Streamlit UI, Analytics, PDF download, curriculum display