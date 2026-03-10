# Intelli-Credit — AI-Powered Corporate Credit Appraisal Engine
#VIDEO LINK - [https://drive.google.com/FILE/D/10U2MWTBX5L9PPKLTPQ5ZG__TKKVTP4--/VIEW?USP=SHARING](https://drive.google.com/file/d/10u2MWtBx5L9PpkltPq5Zg__TkkvtP4--/view?usp=sharing)
## Architecture Overview

```
intelli-credit/
├── backend/                  # FastAPI Python backend
│   ├── app/                  # Config, constants, main entry
│   ├── auth/                 # JWT auth, bcrypt, MongoDB user ops
│   ├── db/                   # Motor async MongoDB connection
│   ├── models/               # Pydantic data models (financial, GST, bank, risk, audit)
│   ├── api/routes/           # REST API routes (auth, ingestion, results, analysis, recommendation)
│   ├── ingestion/            # 5-layer data pipeline
│   │   ├── perception/       # Document classifier (keyword fingerprinting)
│   │   ├── extraction/       # GST, bank, annual report, legal, rating extractors
│   │   ├── normalization/    # Currency (paise), FY period, ratio calculator
│   │   ├── cross_validation/ # GST-Bank reconciler, GST internal reconciler
│   │   └── fraud_detection/  # Circular trading graph, EWS engine (15 flags)
│   ├── analysis/             # ML ensemble: XGBoost + LightGBM + CatBoost + AdaBoost
│   ├── recommendation/       # Five Cs scoring, loan structuring, CAM (Word + PDF)
│   └── research_agent/       # Web crawler, MCA scraper, qualitative note processor
│
├── frontend/                 # React 18 + Vite + Tailwind CSS
│   └── src/
│       ├── pages/            # Login, Register, Dashboard, NewCase, Processing, Results, Analysis, Recommendation, Audit
│       ├── components/       # Auth, layout components
│       ├── store/            # Zustand state (auth, case)
│       └── services/         # Axios API client
│
└── docker-compose.yml        # MongoDB + FastAPI + Nginx
```

## Quick Start

### Local Development

```bash
# 1. Clone and configure
cp .env.example .env   # Edit with your MongoDB URI and SECRET_KEY

# 2. Backend
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# Run MongoDB (local or Atlas)
uvicorn app.main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev   # Starts on http://localhost:5173
```

### Docker Compose

```bash
docker-compose up --build
# Frontend: http://localhost:80
# Backend:  http://localhost:8000
# MongoDB:  mongodb://localhost:27017
```

## Key Features

### Data Ingestion Pipeline (5 Layers)
1. **Perception** — Document classification: GSTR-1/3B/2A/9, Bank (SBI/HDFC/ICICI/AXIS), Annual Reports, Legal Notices, Rating Reports
2. **Extraction** — OCR (PyMuPDF + pdfplumber), JSON portal imports, tabular extraction
3. **Normalization** — All monetary values stored as **paise integers**, Indian FY period parsing (FY23/FY2023/2022-23)
4. **Cross-Validation** — GST-Bank revenue reconciliation, ITC fraud detection (GSTR-3B vs GSTR-2A), GSTR-1 vs GSTR-3B turnover gap
5. **Fraud Detection** — Circular trading graph (NetworkX DFS), shell company scoring, 15 EWS flags

### Analysis Engine
- **Ensemble Model**: XGBoost + LightGBM + CatBoost + AdaBoost → Meta-Learner (Logistic Regression)
- **Credit Score**: 300–850 scale
- **SHAP Explanations**: Feature attribution with Five Cs mapping
- **Early Warning Signals**: 15 flags with severity (CRITICAL/HIGH/MEDIUM/LOW)

### Recommendation & CAM
- APPROVE / APPROVE_WITH_CONDITIONS / REFER / REJECT decision
- MPBF calculation, facility breakup (WC + TL + LC)
- Interest rate = MCLR + risk premium (grade-based) + collateral adjustment
- CAM export: **Word (.docx)** and **PDF** with audit-ready format

### Indian Context
- ₹ → paise conversion throughout (integer arithmetic, no floating point errors)
- ITC fraud detection under CGST Act Section 16 with contingent liability estimation
- Schedule III financial statement mapping (170+ label synonyms)
- GST reconciliation: GSTR-1 vs GSTR-3B vs GSTR-2A vs GSTR-9
- DRT, NCLT, CIRP detection from legal documents

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create credit officer account |
| POST | `/auth/login` | JWT authentication |
| POST | `/cases/` | Create new appraisal case |
| POST | `/cases/{id}/upload` | Upload documents |
| POST | `/cases/{id}/process` | Start ingestion pipeline |
| GET  | `/cases/{id}/status` | Pipeline status polling |
| GET  | `/cases/{id}/results` | Extraction results |
| GET  | `/cases/{id}/ews` | Early Warning Signal report |
| GET  | `/cases/{id}/audit-trail` | Full data lineage |
| POST | `/cases/{id}/analyze` | Run ML ensemble |
| GET  | `/cases/{id}/analysis` | Credit score + SHAP |
| POST | `/cases/{id}/recommend` | Generate recommendation |
| GET  | `/cases/{id}/recommendation` | CAM data |
| GET  | `/cases/{id}/cam/pdf` | Download PDF CAM |
| GET  | `/cases/{id}/cam/word` | Download Word CAM |

## Technology Stack

- **Backend**: Python 3.11, FastAPI, Motor (async MongoDB), PyMuPDF, pdfplumber, NetworkX
- **ML**: XGBoost, LightGBM, CatBoost, scikit-learn, SHAP
- **Documents**: python-docx, ReportLab
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, D3, Zustand
- **Database**: MongoDB (async via Motor)
- **Auth**: JWT (python-jose) + bcrypt
