# INTELLI-CREDIT — COMPLETE MASTER SPECIFICATION
## AI-Powered Corporate Credit Appraisal Engine — Indian Banking Context
### Version 2.0 · Updated 2026-03-10 · Hackathon Build

---

## 1. SYSTEM OVERVIEW

Intelli-Credit is an end-to-end AI-powered Corporate Credit Appraisal Engine for Indian mid-market corporate lending. It ingests multi-format documents, runs a 5-layer processing pipeline, scores the entity using a Triple-Stacking ML ensemble, generates SHAP-driven explainable recommendations, and produces a downloadable Credit Appraisal Memo (CAM).

### Hackathon Evaluation Criteria Coverage

| Criterion | Implementation |
|---|---|
| **Extraction Accuracy** | PyMuPDF + pdfplumber + regex-anchored table extraction. 170+ Indian financial label synonyms. Schedule III mapping. |
| **Research Depth** | **New**: Secondary research agent scrapes live DuckDuckGo & RSS news for company/sector. Triangulated with extracted EWS signals. |
| **Explainability** | **Gemini AI**: Generates a 4-paragraph professional narrative, structured SWOT, and plain-English SHAP driver explanations. |
| **Primary Insights** | **New**: Portal for Credit Officer notes (field visits/interviews). Gemini-enhanced mapping to Five Cs score adjustments. |
| **Indian Context Sensitivity** | GSTR-2A vs 3B ITC reconciliation, NACH bounce detection, MPBF (Tandon Committee), MCA21 filings, DRT/NCLT extraction. |
| **Operational Excellence** | FastAPI + Motor async, React 18 + Vite, JWT auth, background task queue, Loguru verbose logging, MongoDB Atlas. |

---

## 2. THE INTELLI-CREDIT FEATURE MAP

### 2.1. Intelligent Data Ingestion Layer (Perception)
*   **Automatic Multi-Format Classification**: Uses keyword fingerprints to identify 20+ document types (GST, Bank Statements, Annual Reports, Legal Notices, Rating Reports) with a confidence score.
*   **Human-in-the-Loop (HITL) Review**: A dedicated UI stage where analysts can verify or override AI classifications before the heavy processing begins.
*   **Heterogeneous OCR Pipeline**: PyMuPDF for digital extraction + pdfplumber for complex tables + scanned document detection.

### 2.2. Extraction & Normalization Core
*   **Schedule III Financial Parser**: Maps 170+ varied Indian accounting synonyms to a standardized P&L and Balance Sheet schema.
*   **Multi-Bank Statement Engine**: Specialized extractors for HDFC, SBI, ICICI, and AXIS bank formats.
*   **GST Suite**: Deep extraction from GSTR-1, 3B, 2A, and 9/9C, capturing turnover and ITC trends.
*   **Precision Arithmetic**: Uses a paise-integer system to ensure zero floating-point errors in high-value loan calculations.

### 2.3. Fraud Detection & External Intelligence (Digital Manager)
*   **Circular Trading Detector (NetworkX)**: Builds a transaction graph and uses DFS to identify circular invoice chains.
*   **GST-Bank Reconciliation**: Compares declared GST turnover against actual bank deposits (Ratio > 1.15x = Flag).
*   **ITC Fraud Check**: Reconciles GSTR-3B vs GSTR-2A to detect excess credit claims.
*   **Live Secondary Research Agent**: Scrapes live news (DuckDuckGo/RSS) for company and sector risks, triangulating findings with financial flags.

### 2.4. Qualitative Logic (Primary Insights)
*   **Credit Officer Portal**: Interface for recording management interviews and site visit observations.
*   **Gemini-Enhanced Mapping**: Uses Generative AI to map free-text notes into quantitative adjustments across the Five Cs.

### 2.5. Triple-Stacking ML Ensemble
*   **Ensemble Architecture**: Combines XGBoost, LightGBM, and CatBoost with a Logistic Regression meta-learner.
*   **SHAP Explainability**: Visualizes exact risk drivers (e.g., Declining DSCR) for every credit decision.
*   **Risk Grading**: Maps default probabilities to an AAA–D scale.

### 2.6. The Credit Appraisal Memo (CAM) & Reporting
*   **Five Cs Progress Dashboard**: Real-time visualization of entity pillars.
*   **AI Credit Narrative**: Gemini generates professional, multi-paragraph case summaries.
*   **SWOT Synthesis**: Auto-generated grid from financial, research, and EWS signals.
*   **MPBF Calculator**: Tandon Committee Method II implementation.
*   **Multi-Format Export**: One-click professional PDF and Word (.docx) generation.

### 2.7. Global Design System (Aesthetics)
*   **Gray Inlay UI**: Premium, high-density analytics dashboard.
*   **Real-time Pipeline Polling**: Visual feedback of the 5-layer ingestion process.
*   **Design Tokens**: Consistent semantic grays, sharp borders, and JetBrains Mono typography.

---

## 3. MONOREPO STRUCTURE

```
intelli-credit/
├── backend/                          # Python 3.11 · FastAPI · Motor
│   ├── app/
│   │   ├── main.py                   # Lifespan, CORS, router mount, request/response middleware
│   │   └── config.py                 # Settings (env vars, upload dirs, ML model paths)
│   ├── auth/
│   │   ├── routes.py                 # POST /auth/register, POST /auth/login
│   │   ├── service.py                # get_current_user (JWT Bearer), bcrypt verify
│   │   ├── models.py                 # UserCreate, UserResponse Pydantic models
│   │   └── mongo.py                  # MongoDB user CRUD, increment_case_count
│   ├── db/
│   │   ├── mongo.py                  # Motor async client, get_database(), connect/disconnect
│   │   └── indexes.py                # MongoDB index creation on startup
│   ├── models/                       # Pydantic schemas (shared between modules)
│   │   ├── document.py               # DocumentInfo, DocumentType enum (20+ types)
│   │   ├── financial.py              # FinancialStatement, RatioResult
│   │   ├── gst.py                    # GSTReturn, ITCRecord
│   │   ├── bank.py                   # BankStatement, Transaction
│   │   ├── risk.py                   # RiskSignal, EWSFlag
│   │   └── audit.py                  # AuditEntry
│   ├── api/routes/
│   │   ├── auth_routes.py           # POST /auth/register, POST /auth/login
│   │   ├── ingestion_routes.py      # Case CRUD + upload + process + classify (HITL)
│   │   ├── results_routes.py        # /results, /ews, /ratios, /audit-trail
│   │   ├── analysis_routes.py       # /analyze (POST), /analysis (GET)
│   │   ├── recommendation_routes.py # /recommend, /recommendation, /cam/pdf
│   │   └── qualitative_routes.py    # POST /notes (Gemini-mapped primary insights)
│   ├── ai_services/                 # Gemini AI integration client
│   │   ├── gemini_client.py         # Narrative, SWOT, and SHAP explanation generation
│   │   └── fallbacks.py             # Rule-based fallbacks for AI services
│   ├── ingestion/
│   │   ├── orchestrator.py           # 5-layer pipeline runner with per-step Loguru logging
│   │   ├── perception/
│   │   │   ├── classifier.py         # Keyword-fingerprint document classifier (20+ types, confidence score)
│   │   │   └── fingerprints/         # Per-type keyword sets (GST, bank, annual report, legal, rating, etc.)
│   │   ├── extraction/
│   │   │   ├── ocr_engine.py         # PyMuPDF + pdfplumber fallback. Scanned PDF detection.
│   │   │   ├── preprocessors/        # PDF cleaner, image deskewer
│   │   │   ├── table_extraction/     # Lattice + stream table extraction via pdfplumber
│   │   │   ├── text_extraction/      # Section-anchored text parsing
│   │   │   └── document_specific/    # Per-doc-type extractors:
│   │   │       ├── gst_extractor.py          # GSTR-1, 3B, 2A, 9, 9C
│   │   │       ├── bank_extractor.py         # HDFC/SBI/ICICI/AXIS statement formats
│   │   │       ├── annual_report_extractor.py# P&L, Balance Sheet, Cashflow (Schedule III)
│   │   │       ├── legal_extractor.py        # DRT, NCLT, CIRP, court notices
│   │   │       ├── rating_extractor.py       # CRISIL/ICRA/CARE/FITCH rating reports
│   │   │       ├── alm_extractor.py          # Asset-Liability Management data
│   │   │       ├── shareholding_extractor.py # Shareholding pattern (MCA / BSE format)
│   │   │       └── borrowing_profile_extractor.py  # Loan schedules, lender list
│   │   ├── normalization/
│   │   │   ├── currency_normalizer.py  # ₹ lakh/crore/thousand → paise integers
│   │   │   ├── period_normalizer.py    # FY23/FY2023/2022-23/Apr-23 → FY period object
│   │   │   └── ratio_calculator.py     # DSCR, D/E, ICR, EBITDA%, PAT%, Current, Quick, TOL/TNW
│   │   ├── cross_validation/
│   │   │   ├── gst_bank_reconciler.py  # GST annual turnover vs bank deposits (monthly + annual ratio)
│   │   │   └── gst_internal.py         # GSTR-3B vs GSTR-2A ITC delta, turnover suppression
│   │   ├── fraud_detection/
│   │   │   ├── circular_trading/       # NetworkX graph builder, DFS cycle detector, shell scorer
│   │   │   ├── early_warning_signals/
│   │   │   │   └── ews_engine.py       # 15 EWS flags (see Section 5)
│   │   │   └── revenue_inflation/      # Bank deposit ratio spike detection
│   │   ├── indian_context/             # India-specific nuance modules (NACH, MCA, MPBF)
│   │   ├── data_quality/               # Missing field detection, confidence scorer
│   │   └── explainability/             # Risk signal extraction with page_number, keyword, context_text
│   ├── analysis/
│   │   ├── orchestrator.py             # Runs feature engineering → ensemble → SHAP → Five Cs
│   │   ├── ensemble/                   # XGBoost + LightGBM + CatBoost + meta-learner
│   │   │   ├── model_store.py          # Load latest versioned .joblib models
│   │   │   └── stacking.py             # Triple-stacking with Logistic Regression meta-learner
│   │   ├── feature_engineering/        # Build 50-feature vector from extraction results
│   │   └── explainability/             # SHAP TreeExplainer, direction labelling, narrative builder
│   ├── recommendation/
│   │   ├── orchestrator.py             # Five Cs scoring → decision → MPBF → SWOT → CAM
│   │   ├── cam_generator/              # Word (.docx) + PDF (ReportLab) CAM writers
│   │   └── templates/                  # CAM Word template
│   ├── research_agent/                 # Web scraper for secondary research (news, BSE, MCA, eCourts)
│   ├── analysis/training/              # ML training pipeline on Kaggle datasets
│   ├── graph_intelligence/             # Promoter network, director linkage graph
│   ├── promoter_intelligence/          # Promoter/director background checks
│   ├── credit_bureau/                  # CIBIL Commercial, CRISIL integration stubs
│   ├── sector_analysis/                # Sector risk scoring by NIC code
│   ├── stress_testing/                 # Scenario analysis: rate shock, revenue drop
│   ├── rating_simulator/               # Internal rating grade simulator
│   ├── data_lineage/                   # Full data lineage tracking per field
│   ├── anomaly_detection/              # Statistical outlier detection on financials
│   └── explainability/                 # Top-level explainability utilities
│
├── frontend/                           # React 18 · Vite · Pure CSS (JetBrains Mono)
│   └── src/
│       ├── index.css                   # Global design system (gray-inlay tokens, card/button/input classes)
│       ├── App.jsx                     # BrowserRouter + routes + Layout(TopNav) wrapper + Toaster
│       ├── pages/
│       │   ├── LoginPage.jsx           # 2-panel: branding left, form card right (gray inlay)
│       │   ├── RegisterPage.jsx        # Same layout as Login
│       │   ├── DashboardPage.jsx       # KPI band + recent cases + pipeline arch + criteria checklist
│       │   ├── CasesPage.jsx           # Archive: grid rows, status dots, pipeline progress, filter tabs
│       │   ├── NewCasePage.jsx         # 4-step wizard (see Section 7)
│       │   ├── ProcessingPage.jsx      # Real-time pipeline status polling (5-step progress + error display)
│       │   ├── ResultsPage.jsx         # 4-tab: EWS flags | GST analysis | Financial ratios | Documents
│       │   ├── AnalysisPage.jsx        # 4-tab: Decision | SHAP drivers | Five Cs radar | Narrative
│       │   ├── RecommendationPage.jsx  # 5-tab: Overview | Five Cs | SWOT | Research | Eval Criteria
│       │   └── AuditPage.jsx           # Full data lineage + risk level filter
│       ├── components/
│       │   ├── TopNav.jsx              # Fixed top nav: logo + nav links + logout (NO animations)
│       │   ├── auth/ProtectedRoute.jsx # JWT route guard
│       │   ├── NetworkRiskGraph.jsx    # D3 force-directed graph for circular trading
│       │   ├── FinancialRatioCharts.jsx# Recharts ratio trend charts
│       │   └── AnimatedList.jsx        # Simple list animation component
│       ├── store/authStore.js          # Zustand: user, token, setAuth, logout
│       └── services/
│           ├── api.js                  # Axios instance (base URL, JWT interceptor)
│           └── authService.js          # login(), register() wrappers
│
├── .env.example                        # All required environment variables
├── docker-compose.yml                  # MongoDB + FastAPI + Nginx
└── README.md                          # Quick start guide
```

---

## 3. ENVIRONMENT VARIABLES (.env)

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017/intelli_credit

# JWT
SECRET_KEY=your-256-bit-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# File storage
UPLOAD_DIR=./data/uploads
PROCESSED_DIR=./data/processed

# ML Models
MODEL_DIR=./data/models

# Optional: research agent
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ID=

# AI Services
GEMINI_API_KEY=AIzaSyDDeKJuFe7_za7DSh51cxUDOQLpE_x8zHs
GEMINI_MODEL=gemini-1.5-flash
```

---

## 4. MONGODB COLLECTIONS

| Collection | Purpose | Key Fields |
|---|---|---|
| `users` | Credit officer accounts | email, hashed_password, role, case_count |
| `cases` | Appraisal case metadata | case_id, user_id, company_name, company_cin, company_pan, sector, annual_turnover_cr, loan_type, loan_amount_cr, loan_tenure_months, loan_purpose, status, pipeline_status{}, created_at |
| `raw_files` | Uploaded file metadata | file_id, case_id, filename, doc_type, human_override, classification_confidence, file_path, file_size_bytes, page_count |
| `extractions` | Full extraction results | case_id, financial_statements[], ratio_results[], gst_bank_reconciliation{}, gst_internal_reconciliation{}, circular_trading_summary{}, risk_signals[], documents[] |
| `ews_reports` | EWS flag results | case_id, flags[], triggered_count, critical_count, total_score_deduction, overall_risk_classification |
| `audit_trails` | Regulatory data lineage | case_id, finding_type, risk_level, source_document, page_number, extracted_value, delta_paise, narrative, five_c_mapping |
| `ml_results` | Ensemble output | case_id, credit_score, risk_grade, default_probability, shap_result{}, five_cs_score{}, score_narrative |
| `recommendations` | CAM data | case_id, decision, recommended_limit_paise, mpbf_paise, interest_rate_pct, facility_breakup{}, reasons[], covenants[], swot{}, cam_pdf_path, cam_word_path |
| `research_results` | Secondary research | case_id, company, sector, items[], sources_scraped[], generated_at |

---

## 5. COMPLETE API REFERENCE

### Auth
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | {name, email, password, role} | {user_id, token} |
| POST | `/auth/login` | {email, password} | {access_token, token_type} |

### Cases (all require Bearer JWT)
| Method | Path | Description |
|---|---|---|
| POST | `/cases/` | Create case — accepts: company_name, company_cin, company_pan, sector, annual_turnover_cr, loan_type, loan_amount_cr, loan_tenure_months, loan_purpose |
| GET | `/cases/` | List all cases for user (sorted by created_at desc, limit 50) |
| GET | `/cases/{id}` | Get single case by ID |
| POST | `/cases/{id}/upload` | Multi-file upload (PDF/JSON/CSV/XLSX/XLS, max 50MB each) |
| PATCH | `/cases/{id}/classify` | **NEW** Human-in-the-loop classification override: {overrides: {file_id: doc_type}} |
| POST | `/cases/{id}/process` | Start 5-layer ingestion pipeline (background task) |
| GET | `/cases/{id}/status` | Poll pipeline status: {status, pipeline_status{}, error} |
| GET | `/cases/{id}/results` | Full extraction output from `extractions` collection |
| GET | `/cases/{id}/ews` | EWS report: 15 flags with triggered/clear status |
| GET | `/cases/{id}/ratios` | Financial ratio results array (per FY) |
| GET | `/cases/{id}/audit-trail` | Data lineage entries (filterable by risk_level) |
| GET | `/cases/{id}/circular-trading-graph` | Graph nodes + edges for D3 visualisation |
| POST | `/cases/{id}/analyze` | Run ML ensemble (background task) |
| GET | `/cases/{id}/analysis` | Credit score, SHAP, Five Cs, grade, narrative |
| POST | `/cases/{id}/recommend` | Generate CAM: {requested_amount_paise} |
| GET | `/cases/{id}/recommendation` | CAM data (decision, facility, SWOT, covenants) |
| GET | `/cases/{id}/secondary-research` | **NEW** Secondary research items (live or synthesised fallback) |
| GET | `/cases/{id}/cam/pdf` | Download PDF CAM (FileResponse) |
| GET | `/cases/{id}/cam/word` | Download Word CAM (FileResponse) |

---

## 6. 5-LAYER INGESTION PIPELINE

### Layer 1 — PERCEPTION (Document Classification)
- Keyword fingerprint matching per document type
- Returns: `doc_type` (enum), `confidence` (0–1)
- 20+ supported types: gst_gstr1, gst_gstr3b, gst_gstr2a, gst_gstr9, gst_gstr9c, bank_hdfc, bank_sbi, bank_icici, bank_axis, bank_generic, annual_report, shareholding_pattern, alm_data, borrowing_profile, portfolio_performance, legal_notice, rating_report, mca_filing, cam_document, unknown
- **HITL override**: user can correct any classification before pipeline runs. Stored as `human_override: true` in `raw_files`.

### Layer 2 — EXTRACTION
- **OCR**: PyMuPDF primary → pdfplumber fallback for complex tables → scanned PDF detection
- **Table extraction**: lattice (bordered) + stream (whitespace) modes
- **Section detection**: keyword-anchored (e.g. "Profit and Loss", "Schedule III", "Notes to Accounts")
- **Per-document extractors**:
  - `gst_extractor`: GSTR-1/3B/2A/9/9C — turnover, ITC, tax liability, HSN summary
  - `bank_extractor`: HDFC/SBI/ICICI/AXIS formats — monthly deposits, EMI/NACH bounces, OD utilisation
  - `annual_report_extractor`: P&L, Balance Sheet, Cashflow — 170+ label synonym mapping (Schedule III compliant)
  - `legal_extractor`: DRT/NCLT/CIRP case numbers, amounts, status
  - `rating_extractor`: Grade (AAA→D), rating rationale, watch list status from CRISIL/ICRA/CARE/FITCH reports
  - `alm_extractor`: Asset-liability mismatch, maturity buckets
  - `shareholding_extractor`: Promoter %, FII %, DII %, public float
  - `borrowing_profile_extractor`: Lender list, facility type, sanctioned/outstanding amounts
- **Risk signal extraction**: per-signal records include `source_document`, `page_number`, `section_name`, `keyword_matched`, `context_text` (raw paragraph), `confidence`

### Layer 3 — NORMALIZATION
- All monetary values → **paise integers** (₹1 Cr = 10,000,000,00 paise). Zero floating-point errors.
- FY period parsing: "FY23", "FY2023", "2022-23", "Apr-22 to Mar-23", "H1FY24" all → structured period object
- Financial ratio calculation per FY: DSCR, D/E, ICR, EBITDA margin, PAT margin, Current Ratio, Quick Ratio, TOL/TNW

### Layer 4 — CROSS-VALIDATION
- **GST vs Bank Reconciliation**: Monthly GST turnover vs bank deposits. Inflation ratio > 1.15x = flag. Monthly bar chart data stored.
- **GST Internal (ITC)**: GSTR-3B claimed ITC vs GSTR-2A supplier credits. Excess claim = contingent liability. CGST Act Section 16 referenced.
- **Turnover Suppression**: GSTR-1 declared turnover vs GSTR-3B. Gap > 5% = flag.

### Layer 5 — FRAUD DETECTION & EWS
**Circular Trading (NetworkX)**:
- Builds directed transaction graph from GST party data
- DFS cycle detection — identifies circular invoice chains
- Shell company scoring per node
- Outputs: nodes[], edges[], cycles[], total_cycles_detected, high_value_cycles, risk_level

**15 EWS Flags** (each: triggered bool, severity, score_deduction, five_c_impact, evidence_summary, source_documents[]):
1. DSCR_BELOW_1 — DSCR < 1.0
2. DSCR_DECLINING — DSCR falling YoY
3. NACH_BOUNCE_DETECTED — Any ECS/NACH dishonour
4. GOING_CONCERN_DOUBT — Auditor qualification keyword match
5. AUDITOR_CHANGE — Auditor replaced in last 2 years
6. REVENUE_INFLATION_GST — GST vs Bank ratio > 1.25x
7. ITC_EXCESS_CLAIM — GSTR-3B ITC > GSTR-2A credits
8. CIRCULAR_TRADING_DETECTED — NetworkX cycle found
9. DIRECTOR_CIRP_LINKED — Director name in NCLT/DRT notices
10. DEBT_EQUITY_HIGH — D/E > 4x
11. EBITDA_NEGATIVE — EBITDA < 0
12. TURNOVER_DECLINING — Revenue falling 2+ consecutive years
13. MCA_COMPLIANCE_GAP — Late/missing MCA21 filings
14. COLLATERAL_SHORTFALL — Security cover < 1.25x
15. INTEREST_COVERAGE_LOW — ICR < 1.5x

---

## 7. FRONTEND — USER JOURNEY (4 STAGES)

### Stage 1 — Entity Onboarding (`/cases/new` · Step 1)
Form fields:
- Company Name (required)
- Company CIN (optional — for MCA auto-fetch)
- Company PAN (optional)
- Sector (dropdown: 14 sectors including Manufacturing, NBFC, Infrastructure, Real Estate, Pharma, etc.)
- Annual Turnover (₹ Crore)
- Loan Type (dropdown: Term Loan, Cash Credit, OD, WC, LC, BG, Buyers Credit, Mixed)
- Loan Amount (₹ Crore)
- Loan Tenure (months)
- Loan Purpose (free text)

### Stage 2 — Document Upload (Step 2)
- React-Dropzone with multi-file support
- Accepted: PDF, JSON, CSV, XLSX, XLS (≤50MB each)
- Expected document type hints shown per slot:
  - Annual Report / P&L / Balance Sheet
  - Shareholding Pattern
  - ALM (Asset-Liability Management)
  - Borrowing Profile
  - Portfolio Cuts / Performance Data
  - GSTR-1, GSTR-3B, GSTR-2A
  - Bank Statement
  - Rating Report, Legal Notice

### Stage 3 — Human-in-the-Loop Classification Review (Step 3)
- Table shows each uploaded file with AI-detected doc_type + confidence score
- User can override any classification via dropdown (all 12+ doc types listed)
- Override logged as `human_override: true` in MongoDB
- `PATCH /cases/{id}/classify` called with override map before pipeline starts

### Stage 4 — Pipeline Execution (Step 4 + ProcessingPage)
- Summary of entity + loan details confirmed
- "LAUNCH PIPELINE" button triggers `POST /cases/{id}/process`
- Redirects to `/cases/{id}/processing`
- ProcessingPage polls `/cases/{id}/status` every 3s
- Displays 5 pipeline steps with PENDING → RUNNING → DONE/ERROR states
- Shows actual backend error message on failure

---

## 8. RESULTS PAGE (`/cases/:id/results`)

4-tab interface:

### Tab 1 — EWS FLAGS
- All 15 flags: triggered (red/orange/yellow) + clear (dim) sections
- Each triggered flag is **expandable** showing:
  - Evidence summary text
  - Source document filenames
  - Raw context_text (paragraph from PDF that triggered the flag)
  - Keyword matched (e.g. `"going concern"`)
  - Page number in source document
  - Confidence score
- All-clear checks shown as a collapsed grid

### Tab 2 — GST ANALYSIS
- GST vs Bank: annual figures + inflation ratio + monthly bar chart with 1.15x reference line
- ITC Fraud Check: excess claim amount, utilisation rate, turnover suppression %, narrative
- Circular Trading: cycles detected, high-value cycles, value at risk, graph risk level

### Tab 3 — FINANCIAL RATIOS
- Trend line chart: DSCR, EBITDA%, D/E, ICR (multi-line) with DSCR 1.25x benchmark reference line
- Per-FY ratio table with green ✓ / red ✗ vs Indian banking benchmarks:
  - DSCR ≥ 1.25x, ICR ≥ 2.5x, EBITDA ≥ 10%, PAT ≥ 5%
  - D/E ≤ 3x, TOL/TNW ≤ 4x, Current ≥ 1.33x, Quick ≥ 1.0x

### Tab 4 — DOCUMENTS
- All uploaded files with filename, doc_type, classification source (👤 Manual / 🤖 Auto), file size
- Risk signals list: per-signal with severity, signal_type, source_document, page_number, section_name, keyword_matched, context_text snippet

---

## 9. ANALYSIS PAGE (`/cases/:id/analysis`)

4-tab interface:

### Tab 1 — DECISION
- **Grade Ring**: AAA–D grade displayed in a bordered ring with color (white=AAA, orange=BB, red=D)
- **AI Preliminary Recommendation** based on default_probability threshold:
  - < 5% → RECOMMEND: APPROVE
  - 5–15% → APPROVE WITH CONDITIONS
  - 15–30% → REFER TO CREDIT COMMITTEE
  - > 30% → RECOMMEND: DECLINE
- Five Cs animated progress bars (0–100 each, 60/100 pass benchmark line shown)
- Composite score

### Tab 2 — TOP RISK DRIVERS (SHAP)
- Explanation of SHAP methodology
- Horizontal bar chart: top 12 features by |SHAP| (red = risk-increasing, grey = protective)
- **Expandable SHAP cards** (top 10 features) showing:
  - Actual feature value extracted from documents
  - SHAP magnitude and direction
  - "WHY THIS MATTERS" plain-English paragraph
  - Industry benchmark (e.g. "DSCR ≥ 1.25x needed for loan eligibility")
- Feature labels mapped from technical names (e.g. `dscr_fy1` → "Debt Service Coverage (FY1)")

### Tab 3 — FIVE Cs RADAR
- Spider/radar chart for 5 dimensions
- Right panel: what each C measures (Character=audit+directors, Capacity=DSCR+EBITDA, Capital=D/E, Collateral=security, Conditions=sector+GST)

### Tab 4 — AI NARRATIVE
- Full score_narrative text from ML orchestrator
- Model metadata (version, ensemble weights, Val AUC)

**Rerun button** available to re-execute ensemble without navigating away.

---

## 10. RECOMMENDATION PAGE / CAM (`/cases/:id/recommendation`)

5-tab interface:

### Tab 1 — OVERVIEW
- Decision banner (color-coded: green=Approve, blue=Conditional, orange=Refer, red=Decline)
- Key figures: Loan Requested, Recommended Limit, Interest Rate, Tenure
- Facility Structure table (WC + TL + LC + BG breakdown)
- Decision Rationale bullets
- Mandatory Covenants list

### Tab 2 — FIVE Cs ANALYSIS
- Animated progress bars per C with 60/100 benchmark line
- India-Specific Nuances section explaining:
  - GSTR-2A vs 3B ITC Reconciliation
  - NACH Bounce Analysis
  - MPBF Computation (Tandon Committee norms)
  - MCA21 Compliance
  - DRT / NCLT Legal Mapping
  - CIBIL Commercial / CRISIL / ICRA / CARE rating handling

### Tab 3 — SWOT
- 4-quadrant grid: Strengths (green), Weaknesses (red), Opportunities (blue), Threats (orange)
- Each quadrant: bullet list from `recommendation.swot`
- Triangulation note: SWOT synthesised from financial ratios + EWS flags + secondary research + sector data
- GenAI narrative (score_narrative field) shown below

### Tab 4 — SECONDARY RESEARCH
- KPI strip: articles found, positive signals, negative signals, sources scraped
- Items grouped by sentiment: NEGATIVE → POSITIVE → NEUTRAL → MIXED
- Each card: title, source, date, relevance_type badge, sentiment badge, snippet text
- **Triangulation methodology note**: negative news that corroborates an EWS flag elevates that flag's severity
- Data sources: live research_agent DB → synthesised fallback (document risk signals + sector news)
- **Fallback sectors covered**: Manufacturing, NBFC, Infrastructure, Real Estate, Pharmaceuticals
- Each fallback item types: DOCUMENT_SIGNAL, SECTOR_NEWS, REGULATORY

### Tab 5 — EVALUATION CRITERIA
- 6 criteria cards with COVERED/MISSING status for hackathon judges
- Full 4-stage user journey implementation checklist (Stages 1–4 each with bullet list of what was built)

**Downloads**: PDF CAM + Word CAM buttons always visible in header when rec exists.

---

## 11. ML ENSEMBLE

### Architecture: Triple-Stacking
```
Layer 1 (Base learners — trained independently):
  ├── XGBoost (gradient boosting, tabular)
  ├── LightGBM (histogram-based, fast)
  └── CatBoost (handles categoricals natively)

Layer 2 (Meta-learner):
  └── Logistic Regression on OOF predictions from Layer 1

Output: default_probability (0–1), credit_score (300–850)
```

### 50-Feature Vector (key features)
- DSCR (FY1, FY2, FY3)
- EBITDA margin (FY1, FY2)
- Debt/Equity (FY1, FY2)
- Interest Coverage (FY1)
- Current Ratio, Quick Ratio, TOL/TNW
- PAT margin (FY1, FY2)
- GST-Bank inflation ratio
- ITC_inflation_flag (binary)
- Circular trading flag (binary)
- NACH bounce count
- Going concern flag (binary)
- Director CIRP linked (binary)
- Auditor change flag (binary)
- MCA compliance gap flag (binary)
- Turnover YoY growth (FY1→FY2, FY2→FY3)
- Total EWS score deduction
- EWS flags by C (character, capacity, capital, conditions)
- Sector risk score
- Revenue inflation ratio
- Collateral cover ratio

### Model Versioning
- Models saved as `{type}_v{YYYYMMDD_HHMMSS}.joblib`
- `model_store.load_latest()` picks the most recent version automatically
- Val AUC logged on load

### Credit Grade Mapping
| Default Prob | Grade |
|---|---|
| < 1% | AAA |
| 1–3% | AA |
| 3–7% | A |
| 7–15% | BBB |
| 15–25% | BB |
| 25–40% | B |
| 40–60% | C |
| > 60% | D |

---

## 12. FIVE Cs SCORING

| C | Weight | Key Sub-signals |
|---|---|---|
| Character | 20% | Audit opinion (going concern), director DRT/CIRP links, MCA compliance, auditor change |
| Capacity | 30% | DSCR, Interest Coverage, EBITDA margin, PAT trend, NACH bounce count |
| Capital | 25% | D/E, TOL/TNW, undisclosed borrowings, promoter equity infusion |
| Collateral | 15% | Security coverage ratio, nature of security, lien quality |
| Conditions | 10% | Sector risk, GST compliance score, ITC fraud signals, circular trading presence |

Score range: 0–100 per C. Composite = weighted average. Pass threshold: 60/100 composite.

---

## 13. RECOMMENDATION ENGINE

### Decision Logic
| Condition | Decision |
|---|---|
| Composite ≥ 70 AND DP < 10% AND no CRITICAL flags | APPROVE |
| Composite 55–70 AND DP < 20% | APPROVE WITH CONDITIONS |
| Composite 40–55 OR DP 20–35% | REFER TO CREDIT COMMITTEE |
| Composite < 40 OR DP > 35% OR CRITICAL flag triggered | DECLINE |

### Interest Rate Formula
```
Rate = MCLR_base + risk_premium(grade) + collateral_adjustment
risk_premium: AAA=0.25, AA=0.5, A=0.75, BBB=1.0, BB=2.0, B=3.5, C/D=5.0+
collateral_adj: secured=-0.25, unsecured=+0.5
```

### MPBF (Maximum Permissible Bank Finance)
Tandon Committee Method II:
```
MPBF = 0.75 × (Current Assets - Core Current Liabilities)
```

### Facility Breakup
- Working Capital (CC/OD): up to MPBF
- Term Loan: requested - WC allocation
- LC/BG: based on trade cycle and sector

### SWOT Generation
Synthesised from: EWS triggers → Weaknesses/Threats | strong ratios → Strengths | sector outlook → Opportunities

---

## 14. CAM DOCUMENT STRUCTURE

Both Word (.docx) and PDF outputs contain:
1. Cover page: Entity name, CIN, PAN, date, analyst name
2. Executive Summary
3. Entity Overview (sector, turnover, loan details)
4. Financial Analysis (ratio trends per FY)
5. Five Cs Assessment (scored, with evidence)
6. GST & Bank Reconciliation
7. Fraud & EWS Analysis
8. Secondary Research Summary
9. SWOT Analysis
10. ML Model Output (grade, score, SHAP top drivers)
11. Recommendation & Facility Structure
12. Covenants & Conditions
13. Appendix: Data Sources & Audit Trail

---

## 15. DESIGN SYSTEM

### Color Tokens
```
bg-black   : #000000  — page background
bg-1       : #0d0d0d  — card inlay (dark gray)
bg-2       : #141414  — elevated card / hover
bg-nav     : #080808  — topnav, tab bars
border-1   : #1c1c1c  — section dividers
border-2   : #2a2a2a  — default card border
border-3   : #444     — emphasis
text-white : #f0f0f0
text-gray  : #888
text-muted : #555
text-dim   : #333
danger     : #ff4444
warning    : #ff8800
success    : #22dd66
info       : #4488ff
```

### Typography
- Font: JetBrains Mono (Google Fonts)
- Weights: 300 (body), 400 (normal), 500 (medium), 700 (bold), 800 (headings)
- All headings: uppercase, letter-spacing 2px

### CSS Utility Classes
`.card` `.card-2` `.panel` `.kpi-cell` `.label` `.btn-primary` `.badge` `.badge-success/warning/danger/muted` `.row-list` `.row-item` `.row-header` `.progress-track` `.progress-fill` `.tab-bar` `.tab-btn` `.section-header` `.divider` `.mono` `.spin` `.pulse`

### Navigation
- Fixed top bar (`height: 50px`, `background: #080808`, `border-bottom: #1e1e1e`)
- Logo: `INTELLI·CREDIT` (·  in gray)
- Links: DASHBOARD | ARCHIVE | NEW CASE
- Active link: white background, black text
- Right: user name (gray) + LOGOUT button
- **Zero animations — no Framer Motion on nav**

---

## 16. SECONDARY RESEARCH AGENT

### Endpoint: `GET /cases/{id}/secondary-research`

**Priority 1 — Live agent results** (from `research_results` collection):
- Populated when research_agent scraper has run

**Priority 2 — Synthesised fallback** (always works for demo):
- EWS risk signals from extraction → formatted as research cards
- Sector-specific news lookup (Manufacturing, NBFC, Infrastructure, Real Estate, Pharma)
- MCA regulatory context card
- Returns: items[], sources_scraped[], mode="synthesised"

### Each research item schema:
```json
{
  "title": "string",
  "source": "Economic Times | BSE | MCA21 | eCourts",
  "snippet": "150-300 char excerpt",
  "sentiment": "POSITIVE | NEGATIVE | NEUTRAL | MIXED",
  "date": "YYYY-MM-DD",
  "relevance_type": "SECTOR_NEWS | DOCUMENT_SIGNAL | REGULATORY | LEGAL",
  "confidence": 0.0-1.0
}
```

### Triangulation Logic
- Negative news + matching EWS flag → elevates flag severity one level
- Positive sector news + strong ratios → adds to Strengths in SWOT
- Legal/regulatory items → mapped to Character C in Five Cs

---

## 17. TECH STACK SUMMARY

### Backend
- Python 3.11
- FastAPI (async, background tasks)
- Motor (async MongoDB driver)
- Loguru (structured logging — every API call logged with method/path/status/latency)
- PyMuPDF (fitz) — PDF text + image extraction
- pdfplumber — table extraction
- NetworkX — circular trading graph
- XGBoost, LightGBM, CatBoost, scikit-learn, SHAP
- python-docx, ReportLab — CAM generation
- passlib[bcrypt], python-jose — auth

### Frontend
- React 18 + Vite
- React Router DOM v6
- Zustand (auth state)
- Axios (API client with JWT interceptor)
- Recharts (line, bar, radar charts)
- react-dropzone (file upload)
- react-hot-toast (notifications)
- Pure CSS (JetBrains Mono — no Tailwind, no Framer Motion on nav)

### Database
- MongoDB (Motor async)  
- Collections: users, cases, raw_files, extractions, ews_reports, audit_trails, ml_results, recommendations, research_results

### DevOps
- Docker + docker-compose (MongoDB + FastAPI + Nginx)
- Uvicorn (ASGI server with --reload)
- CORS: all origins in dev, restrict in prod

---

## 18. RUNNING LOCALLY

```bash
# 1. Configure environment
cp .env.example .env
# Edit MONGODB_URI and SECRET_KEY

# 2. Backend (from repo root)
cd intelli-credit
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm

# Start backend (from repo root, not backend/)
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 19. KNOWN LIMITATIONS & NEXT STEPS

| Item | Status | Notes |
|---|---|---|
| Live research agent scraping | Stub | Fallback always returns synthesised data |
| CIBIL Commercial API | Stub | Rating extractor works on PDF reports |
| MCA21 API | Stub | Legal extractor works on uploaded notices |
| eCourts scraping | Stub | Legal extractor works on uploaded docs |
| SWOT auto-generation | Partial | Generated by recommendation orchestrator from EWS + ratios |
| Dynamic output schema | Partial | Fixed 50-feature schema; user override via HITL classification |
| Sector stress testing | Module exists | Not exposed in UI yet |
| Rating simulator | Module exists | Not exposed in UI yet |
| Promoter network graph | Module exists | Not exposed in UI yet |
| ALM gap analysis | Extractor exists | Results not surfaced in Results UI |
| Portfolio performance analytics | Extractor exists | Not surfaced in UI yet |

---

## 20. CHRONOLOGICAL CHANGELOG (Hackathon Build)

### [2.0.0] - 2026-03-10
#### Added
- **Gemini AI Service Layer**: Integrated `google-generativeai` for professional Credit Narrative generation, structured SWOT synthesis, and plain-English SHAP explanations.
- **Primary Insight Portal**: Added UI and Backend for "Credit Officer Notes" (Field Visits/Interviews). AI maps these qualitative inputs to Five Cs score adjustments (±15 pts).
- **Live Secondary Research**: Upgraded `NewsScraperAsync` to perform live DuckDuckGo and RSS scraping for company/sector intel. Resulting scores are fed into the ML feature vector.
- **Evaluation Criteria Dashboard**: New tab in Recommendation Page explicitly mapping implementation details to hackathon judging criteria.
- **Qualitative Routes**: New API endpoint `/cases/{id}/notes` for managing primary insights.

#### Changed
- **UI/UX Overhaul**: Rebuilt the entire design system using a "Gray Inlay" aesthetic (layered grays, off-black background, JetBrains Mono font).
- **Dashboard Refinement**: Removed greeting bar; added pipeline architecture visual and hackathon checklist.
- **New Case Wizard**: Redesigned Step 2 to highlight "5 Critical Document Types" required by the hackathon problem statement.
- **Ingestion Orchestrator**: Integrated live research scraping as "Step 0" of the pipeline.
- **Recommendation Orchestrator**: Hooked Gemini AI and Qualitative Adjustments into the final CAM generation flow.

#### Fixed
- Fixed layout double-padding issues in `App.jsx`.
- Standardized currency normalization for all bank and GST inputs to 100% paise-integer arithmetic.
- Refactored `RecommendationPage.jsx` to use centralized CSS tokens from `index.css`.
