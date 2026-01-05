# AI Codebase Onboarding Assistant 🚀

An AI-powered assistant that helps developers understand, explore, and onboard onto any codebase using natural language queries with grounded, source-linked answers.

---

## 🎯 Problem

Developers joining new teams often struggle to understand large, unfamiliar codebases. 
Documentation is outdated, onboarding is slow, and productivity drops in the first weeks.

---

## 💡 Solution

AI Codebase Onboarding Assistant uses:
- **Azure OpenAI** for reasoning over code
- **Azure AI Search** for semantic vector search
- **FastAPI** for scalable backend APIs

Developers can ask questions like:
- *Where do I start?*
- *How do I run this project?*
- *What are the main API endpoints?*
- *Explain the architecture*

And receive **grounded answers with source references**.

---

## ⚠️ Demo Notice (Important)

> This repository is **pre-indexed for demo stability**.
In production, the platform supports ingestion of **any GitHub or internal repository**. 
The current demo indexes this repository to ensure consistent results for judges.

---

## 🏗️ Architecture

- **Backend:** Python, FastAPI, Azure OpenAI, Azure AI Search
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **AI Models:**
  - GPT-4o-mini (chat)
  - text-embedding-3-small (vector search)

---

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
|------|---------|------------|
| GET | `/api/predefined/where-to-start` | Onboarding guidance |
| POST | `/api/chat` | Ask questions about the codebase |
| POST | `/api/ingest` | Repository ingestion |
| GET | `/api/health` | Health check |
| GET | `/docs` | Swagger UI |

---

## ▶️ Running Locally

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python run_dev.py
```

App runs at: http://localhost:8002

## 🔐 Environment Variables

Copy `.env.example` to `.env` and fill in your Azure credentials.

```bash
cp .env.example .env
```

## 🧪 Testing

```bash
python test_demo_workflow.py
```

✅ All demo workflows validated (8/8 tests passing)

## 🏆 Built for Imagine Cup 2026

This project is an MVP built for the Microsoft Imagine Cup 2026, focusing on developer education, onboarding, and productivity through AI.