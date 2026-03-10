from fastapi import APIRouter, Depends, HTTPException
from auth.service import get_current_user
from auth.models import UserResponse
from db.mongo import get_database

router = APIRouter()


@router.get("/{case_id}/results")
async def get_results(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    extraction = await db.extractions.find_one({"case_id": case_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Results not yet available")
    extraction["_id"] = str(extraction["_id"])
    return extraction


@router.get("/{case_id}/audit-trail")
async def get_audit_trail(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    entries = await db.audit_trails.find({"case_id": case_id}).sort("risk_level", -1).to_list(length=200)
    for e in entries:
        e["_id"] = str(e["_id"])
    return {"entries": entries, "count": len(entries)}


@router.get("/{case_id}/ews")
async def get_ews(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    report = await db.ews_reports.find_one({"case_id": case_id})
    if not report:
        raise HTTPException(status_code=404, detail="EWS report not yet available")
    report["_id"] = str(report["_id"])
    return report


@router.get("/{case_id}/ratios")
async def get_ratios(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    extraction = await db.extractions.find_one({"case_id": case_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Data not yet available")
    return {"ratios": extraction.get("ratio_results", [])}


@router.get("/{case_id}/circular-trading-graph")
async def get_circular_trading_graph(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    extraction = await db.extractions.find_one({"case_id": case_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Data not yet available")
    graph_data = extraction.get("circular_trading_graph", {"nodes": [], "edges": []})
    return graph_data
