from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List
from datetime import datetime
from loguru import logger
import uuid
import os
import asyncio

from auth.service import get_current_user
from auth.models import UserResponse
from auth.mongo import increment_case_count
from db.mongo import get_database
from models.document import DocumentInfo, DocumentType
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".json", ".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/")
async def create_case(
    payload: dict,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case_id = str(uuid.uuid4())
    now = datetime.utcnow()
    company = payload.get("company_name", "")
    logger.info(f"CREATE CASE | user={current_user.email} | company='{company}' | case={case_id[:8]}")
    doc = {
        "case_id": case_id,
        "user_id": current_user.id,
        # Entity info
        "company_name":       company,
        "company_cin":        payload.get("company_cin", ""),
        "company_pan":        payload.get("company_pan", ""),
        "sector":             payload.get("sector", ""),
        "annual_turnover_cr": payload.get("annual_turnover_cr"),
        # Loan details
        "loan_type":          payload.get("loan_type", ""),
        "loan_amount_cr":     payload.get("loan_amount_cr"),
        "loan_tenure_months": payload.get("loan_tenure_months"),
        "loan_purpose":       payload.get("loan_purpose", ""),
        # Pipeline state
        "status": "created",
        "pipeline_status": {
            "perception": "pending",
            "extraction": "pending",
            "normalization": "pending",
            "cross_validation": "pending",
            "fraud_detection": "pending",
        },
        "documents": [],
        "created_at": now,
        "updated_at": now,
        "processing_time_seconds": 0,
    }
    await db.cases.insert_one(doc)
    await increment_case_count(current_user.id)
    logger.success(f"Case created: {case_id} | sector={payload.get('sector')} | loan=₹{payload.get('loan_amount_cr')} Cr")
    return {"case_id": case_id, "status": "created"}


@router.patch("/{case_id}/classify")
async def update_classifications(
    case_id: str,
    payload: dict,
    current_user: UserResponse = Depends(get_current_user),
):
    """Human-in-the-loop: accept user overrides for document classifications."""
    db = get_database()
    overrides = payload.get("overrides", {})
    updated = 0
    for file_id, doc_type in overrides.items():
        result = await db.raw_files.update_one(
            {"file_id": file_id, "case_id": case_id},
            {"$set": {"doc_type": doc_type, "human_override": True}}
        )
        if result.modified_count:
            updated += 1
            logger.info(f"[{case_id[:8]}] Classification override: {file_id[:8]} → '{doc_type}'")
    return {"updated": updated}


@router.post("/{case_id}/upload")
async def upload_documents(
    case_id: str,
    files: List[UploadFile] = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    upload_dir = os.path.join(settings.UPLOAD_DIR, case_id)
    os.makedirs(upload_dir, exist_ok=True)
    logger.info(f"UPLOAD | case={case_id[:8]} | files={len(files)} | dir={upload_dir}")

    uploaded_docs = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        logger.debug(f"  Receiving: {file.filename} (ext={ext})")

        if ext not in ALLOWED_EXTENSIONS:
            logger.error(f"  REJECTED: {file.filename} — extension '{ext}' not allowed")
            raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use: PDF, JSON, CSV, XLSX")

        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        logger.debug(f"  Size: {size_mb:.1f}MB")

        if len(content) > MAX_FILE_SIZE:
            logger.error(f"  REJECTED: {file.filename} — {size_mb:.1f}MB exceeds 50MB limit")
            raise HTTPException(status_code=400, detail=f"File {file.filename} is {size_mb:.1f}MB — exceeds 50MB limit")

        file_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f"{file_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        logger.success(f"  Saved: {file.filename} → {file_path}")

        doc_info = {
            "file_id": file_id,
            "filename": file.filename,
            "doc_type": DocumentType.UNKNOWN.value,
            "classification_confidence": 0.5,
            "page_count": 0,
            "is_scanned": False,
            "ocr_applied": False,
            "file_size_bytes": len(content),
            "file_path": file_path,
            "upload_timestamp": datetime.utcnow().isoformat(),
        }
        uploaded_docs.append(doc_info)

    await db.cases.update_one(
        {"case_id": case_id},
        {
            "$push": {"documents": {"$each": [d["file_id"] for d in uploaded_docs]}},
            "$set": {"status": "uploading", "updated_at": datetime.utcnow()},
        },
    )

    # Store raw file metadata, convert ObjectId before returning
    for doc in uploaded_docs:
        doc["case_id"] = case_id
        await db.raw_files.insert_one(doc)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    logger.success(f"UPLOAD COMPLETE | case={case_id[:8]} | {len(uploaded_docs)} files saved")
    return {"uploaded": len(uploaded_docs), "documents": uploaded_docs}


@router.post("/{case_id}/process")
async def process_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    raw_files = await db.raw_files.find({"case_id": case_id}).to_list(length=50)
    file_paths = [f["file_path"] for f in raw_files if "file_path" in f]
    # Build override map: file_path → user-confirmed doc_type
    path_to_doctype = {
        f["file_path"]: f.get("doc_type", "unknown")
        for f in raw_files if "file_path" in f
    }

    logger.info(f"PROCESS START | case={case_id[:8]} | {len(file_paths)} files queued")
    for fp, dt in path_to_doctype.items():
        human = "👤" if raw_files[0].get("human_override") else "🤖"
        logger.debug(f"  {human} [{dt}] {fp.split(chr(92))[-1]}")

    if not file_paths:
        logger.error(f"PROCESS FAILED | case={case_id[:8]} | No files in raw_files collection!")
        raise HTTPException(status_code=400, detail="No uploaded files found. Please upload documents first.")

    from ingestion.orchestrator import IngestionOrchestrator
    orchestrator = IngestionOrchestrator()
    background_tasks.add_task(orchestrator.run, case_id, file_paths)
    return {"message": "Processing started", "case_id": case_id}


@router.get("/{case_id}/status")
async def get_case_status(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "case_id": case_id,
        "status": case["status"],
        "pipeline_status": case.get("pipeline_status", {}),
        "updated_at": case.get("updated_at"),
        "processing_time_seconds": case.get("processing_time_seconds", 0),
        "error": case.get("error"),
    }


@router.get("/")
async def list_cases(current_user: UserResponse = Depends(get_current_user)):
    db = get_database()
    cursor = db.cases.find({"user_id": current_user.id}).sort("created_at", -1).limit(50)
    cases = []
    async for case in cursor:
        case["_id"] = str(case["_id"])
        cases.append(case)
    return {"cases": cases}


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case["_id"] = str(case["_id"])
    return case
