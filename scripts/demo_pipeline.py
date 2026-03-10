#!/usr/bin/env python3
"""
demo_pipeline.py
Full end-to-end demo of Intelli-Credit system.
Creates synthetic documents, runs the entire pipeline,
and prints a formatted report.

Usage:
    python scripts/demo_pipeline.py
    python scripts/demo_pipeline.py --company "Acme Industries Ltd" --cin L12345MH2010PLC200000
    python scripts/demo_pipeline.py --use-real-docs path/to/docs/
"""
import os
import sys
import json
import asyncio
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from loguru import logger
logger.remove()
logger.add(sys.stdout, format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level}</level> | {message}", level="INFO")


# ── Synthetic Document Generation ────────────────────────────────────────────

def generate_synthetic_gstr1(company_name: str, gstin: str) -> dict:
    """Generate realistic GSTR-1 JSON as exported from GST portal."""
    return {
        "gstin": gstin,
        "fp": "032023",
        "b2b": [
            {"ctin": "27AABCU9603R1ZV", "inv": [
                {"idt": "15/07/2022", "val": 12500000},
                {"idt": "28/09/2022", "val": 8750000},
            ]},
            {"ctin": "29AAACS8919K2Z9", "inv": [
                {"idt": "12/01/2023", "val": 22000000},
            ]},
        ],
        "b2cl": [{"inv": [{"val": 5000000}]}],
        "exp": [],
    }


def generate_synthetic_gstr3b(gstin: str) -> dict:
    return {
        "gstin": gstin,
        "ret_period": "032023",
        "sup_details": {"osup_det": {"txval": 48250000}},
        "itc_elg": {
            "itc_avl": {"igst": 4200000, "cgst": 1800000, "sgst": 1800000, "cess": 0},
            "itc_rev": {"igst": 0, "cgst": 0, "sgst": 0, "cess": 0},
        },
        "vtax": {"igst": 5400000},
    }


def generate_synthetic_gstr2a(gstin: str) -> dict:
    return {
        "gstin": gstin,
        "b2b": [
            {"ctin": "24AAACR5055K1Z5", "inv": [{"val": 18000000}]},
            {"ctin": "08AABCA1234B1Z9", "inv": [{"val": 9500000}]},
        ],
    }


def generate_synthetic_bank_csv(company_name: str) -> str:
    """Generate a simplified bank statement CSV."""
    rows = [
        "Txn Date,Description,Ref No,Withdrawal Amt,Deposit Amt,Balance",
        "01/04/2022,Opening Balance,,,,15000000",
        "05/04/2022,NEFT/RTGS-Buyer1,,,,10000000,25000000",
        "12/04/2022,NACH-EMI-HDFC-Term Loan,,2500000,,22500000",
        "30/06/2022,RTGS-Buyer2,,,18000000,40500000",
        "15/09/2022,NACH-EMI-HDFC-Term Loan,,2500000,,38000000",
        "28/03/2023,NEFT-Buyer1-Year-End,,,15000000,53000000",
        "31/03/2023,NACH-EMI-HDFC-Term Loan,,2500000,,50500000",
    ]
    return "\n".join(rows)


def generate_synthetic_annual_report_text() -> str:
    """Generate minimal parseable annual report text."""
    return """
INDEPENDENT AUDITOR'S REPORT

To the Members of Demo Company Limited

Opinion

We have audited the financial statements of Demo Company Limited (the "Company").
In our opinion, the accompanying financial statements give a true and fair view.
The financial statements referred to above have been prepared in accordance with Ind AS.

DIRECTORS' REPORT

Your Directors present the Annual Report for the financial year ended March 31, 2023.

Financial Highlights (₹ in Lakhs):
                          FY 2022-23    FY 2021-22
Revenue from operations   4,825.00      4,200.00
EBITDA                      820.25        700.10
Profit Before Tax           510.00        420.00
Profit After Tax            380.00        310.00
Total Debt                2,100.00      2,400.00
Net Worth                 1,850.00      1,580.00
Total Assets              5,200.00      5,000.00
Current Assets            2,400.00      2,200.00
Current Liabilities       1,600.00      1,500.00

MANAGEMENT DISCUSSION AND ANALYSIS

The Company continues to focus on operational excellence and cost optimization.
Revenue grew by 15% driven by strong order book and capacity utilization.
EBITDA margins improved to 17% reflecting better operational leverage.

There are no going concern issues and the Company is financially stable.
"""


# ── Pipeline Steps ─────────────────────────────────────────────────────────

async def step_create_case(company_name: str, cin: str) -> str:
    logger.info(f"Step 1: Creating case for '{company_name}' (CIN: {cin})")
    from db.mongo import connect_to_mongo
    from datetime import datetime
    import uuid

    await connect_to_mongo()
    from db.mongo import get_database
    db = get_database()

    case_id = str(uuid.uuid4())[:8].upper()
    case = {
        "case_id": case_id,
        "company_name": company_name,
        "cin": cin,
        "status": "created",
        "pipeline_status": {},
        "created_by": "demo_user",
        "created_at": datetime.utcnow(),
        "documents": [],
    }
    await db.cases.insert_one(case)
    logger.info(f"  ✓ Case created: {case_id}")
    return case_id


async def step_save_documents(case_id: str, tmpdir: str, company_name: str) -> list:
    logger.info(f"Step 2: Saving synthetic documents")
    from db.mongo import get_database
    db = get_database()

    gstin = "27AABCD1234E1Z5"
    docs = []

    # GSTR-1 JSON
    gstr1 = generate_synthetic_gstr1(company_name, gstin)
    p = os.path.join(tmpdir, "gstr1.json")
    with open(p, "w") as f: json.dump(gstr1, f)
    docs.append({"path": p, "type": "GSTR1", "filename": "gstr1.json"})

    # GSTR-3B
    gstr3b = generate_synthetic_gstr3b(gstin)
    p = os.path.join(tmpdir, "gstr3b.json")
    with open(p, "w") as f: json.dump(gstr3b, f)
    docs.append({"path": p, "type": "GSTR3B", "filename": "gstr3b.json"})

    # GSTR-2A
    gstr2a = generate_synthetic_gstr2a(gstin)
    p = os.path.join(tmpdir, "gstr2a.json")
    with open(p, "w") as f: json.dump(gstr2a, f)
    docs.append({"path": p, "type": "GSTR2A", "filename": "gstr2a.json"})

    # Bank Statement CSV
    bank_csv = generate_synthetic_bank_csv(company_name)
    p = os.path.join(tmpdir, "bank_statement.csv")
    with open(p, "w") as f: f.write(bank_csv)
    docs.append({"path": p, "type": "BANK_STATEMENT", "filename": "bank_statement.csv"})

    # Annual Report TXT (since we're not generating a full PDF)
    annual = generate_synthetic_annual_report_text()
    p = os.path.join(tmpdir, "annual_report.txt")
    with open(p, "w") as f: f.write(annual)
    docs.append({"path": p, "type": "ANNUAL_REPORT", "filename": "annual_report.txt"})

    # Update case
    await db.cases.update_one(
        {"case_id": case_id},
        {"$set": {"documents": docs, "status": "documents_uploaded"}}
    )
    logger.info(f"  ✓ {len(docs)} documents uploaded")
    return docs


async def step_run_ingestion(case_id: str, docs: list) -> dict:
    logger.info(f"Step 3: Running ingestion pipeline")
    from ingestion.orchestrator import IngestionOrchestrator
    orchestrator = IngestionOrchestrator()
    result = await orchestrator.run(case_id, docs)
    logger.info(f"  ✓ Ingestion complete — Status: {result.get('status', '?')}")
    return result


async def step_run_analysis(case_id: str) -> dict:
    logger.info(f"Step 4: Running ML analysis + SHAP")
    from analysis.orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    result = await orchestrator.run(case_id)
    logger.info(f"  ✓ Credit Score: {result.get('credit_score')} | Grade: {result.get('risk_grade')} | DP: {result.get('default_probability'):.1%}")
    return result


async def step_generate_recommendation(case_id: str, requested_amount_crore: float = 50.0) -> dict:
    logger.info(f"Step 5: Generating recommendation (Requested: ₹{requested_amount_crore} Cr)")
    from recommendation.orchestrator import RecommendationOrchestrator
    orchestrator = RecommendationOrchestrator()
    amount_paise = int(requested_amount_crore * 1e7 * 100)
    result = await orchestrator.run(case_id, requested_amount_paise=amount_paise)
    logger.info(f"  ✓ Decision: {result.get('decision')} | Limit: ₹{result.get('recommended_limit_paise', 0)/1e9:.1f} Cr")
    return result


async def step_generate_cam(case_id: str, output_dir: str):
    logger.info(f"Step 6: Generating CAM documents")
    from db.mongo import get_database
    db = get_database()

    analysis = await db.analyses.find_one({"case_id": case_id})
    recommendation = await db.recommendations.find_one({"case_id": case_id})
    case = await db.cases.find_one({"case_id": case_id})

    if recommendation:
        try:
            from recommendation.cam_generator.word_exporter import generate_cam_word
            docx_path = os.path.join(output_dir, f"CAM_{case_id}.docx")
            generate_cam_word(case, analysis, recommendation, docx_path)
            logger.info(f"  ✓ Word CAM: {docx_path}")
        except Exception as e:
            logger.warning(f"  Word CAM failed: {e}")

        try:
            from recommendation.cam_generator.pdf_exporter import generate_cam_pdf
            pdf_path = os.path.join(output_dir, f"CAM_{case_id}.pdf")
            generate_cam_pdf(case, analysis, recommendation, pdf_path)
            logger.info(f"  ✓ PDF CAM: {pdf_path}")
        except Exception as e:
            logger.warning(f"  PDF CAM failed: {e}")


def print_summary(case_id, analysis, recommendation):
    print("\n" + "=" * 65)
    print("           INTELLI-CREDIT DEMO — ANALYSIS SUMMARY")
    print("=" * 65)
    print(f"  Case ID      : {case_id}")
    print(f"  Credit Score : {analysis.get('credit_score', 'N/A')} / 850")
    print(f"  Risk Grade   : {analysis.get('risk_grade', 'N/A')}")
    print(f"  Default Prob : {analysis.get('default_probability', 0):.1%}")
    print(f"  Model Used   : {analysis.get('model_version', 'N/A')}")
    print(f"  SHAP Method  : {analysis.get('shap_result', {}).get('shap_method', 'N/A')}")

    fcs = analysis.get("five_cs_score", {})
    if fcs:
        print(f"\n  Five Cs Scoring:")
        for c, score in fcs.items():
            bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
            print(f"    {c:12s} [{bar}] {score:.0f}/100")

    print(f"\n  DECISION     : {recommendation.get('decision', 'N/A')}")
    print(f"  Limit        : ₹{recommendation.get('recommended_limit_paise', 0)/1e9:.2f} Cr")
    print(f"  Interest     : {recommendation.get('interest_rate_pct', 'N/A')}% p.a.")

    shap = analysis.get("shap_result", {})
    drivers = shap.get("top_risk_drivers", [])
    if drivers:
        print(f"\n  Top Risk Drivers (SHAP):")
        for i, d in enumerate(drivers[:5], 1):
            print(f"    {i}. {d}")

    print("=" * 65)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Intelli-Credit Full Pipeline Demo")
    parser.add_argument("--company", default="Acme Industries Limited", help="Company name")
    parser.add_argument("--cin", default="L12345MH2010PLC200000", help="CIN")
    parser.add_argument("--amount", type=float, default=50.0, help="Loan amount in Crore")
    parser.add_argument("--output", default="./demo_output", help="Output directory for CAM files")
    parser.add_argument("--train-first", action="store_true", help="Train ML model before demo")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Step 0: Optionally train model
    if args.train_first:
        logger.info("Step 0: Training ML ensemble (--no-tune for speed)...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "ml_training/run_training.py", "--no-tune"],
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("  ✓ Training complete")
        else:
            logger.warning(f"  Training had issues: {result.stderr[-500:]}")

    with tempfile.TemporaryDirectory() as tmpdir:
        case_id = await step_create_case(args.company, args.cin)
        docs = await step_save_documents(case_id, tmpdir, args.company)
        await step_run_ingestion(case_id, docs)
        analysis = await step_run_analysis(case_id)
        recommendation = await step_generate_recommendation(case_id, args.amount)
        await step_generate_cam(case_id, args.output)
        print_summary(case_id, analysis, recommendation)

    logger.info(f"\n🏆 Demo complete. CAM files saved to: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    asyncio.run(main())
