from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from loguru import logger

from auth.service import get_current_user
from auth.models import UserResponse
from db.mongo import get_database
from research_agent.primary_input_handler import PrimaryInputHandler, QualitativeAdjustment

router = APIRouter()
handler = PrimaryInputHandler()

@router.post("/{case_id}/notes")
async def add_qualitative_note(
    case_id: str,
    payload: dict,
    current_user: UserResponse = Depends(get_current_user),
):
    """Save a credit officer note and process it for Five Cs adjustment."""
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note_text = payload.get("note", "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text cannot be empty")

    # Process via rule-based handler (baseline)
    adjustment = handler.process_qualitative_note(note_text, case_id)

    # NEW: Attempt Gemini enhancement for better understanding
    try:
        from ai_services.gemini_client import _generate
        prompt = f"""You are a Credit Risk AI. Analyze this Credit Officer's qualitative note:
"{note_text}"

Map it to one of the Five Cs of Credit: Character, Capacity, Capital, Collateral, Conditions.
Assign a score adjustment between -10.0 (severe risk) and +10.0 (strong positive).

Return JSON only:
{{
  "dimension": "Capacity",
  "adjustment": -5.0,
  "reason": "Brief explanation of adjustment based on the note."
}}"""
        import json, re
        gemini_text = await _generate(prompt)
        match = re.search(r'\{[\s\S]*\}', gemini_text)
        if match:
            gem_data = json.loads(match.group())
            adjustment.dimension = gem_data.get("dimension", adjustment.dimension)
            adjustment.adjustment = gem_data.get("adjustment", adjustment.adjustment)
            adjustment.reason = gem_data.get("reason", adjustment.reason)
            logger.info(f"[{case_id[:8]}] Gemini enhanced qualitative note processing")
    except Exception as e:
        logger.warning(f"[{case_id[:8]}] Gemini qualitative enhancement failed, using rules: {e}")

    # Store in DB
    note_doc = {
        "case_id": case_id,
        "user_id": current_user.id,
        "note": note_text,
        "processed_adjustment": adjustment.dict(),
        "created_at": datetime.utcnow()
    }
    
    await db.qualitative_notes.insert_one(note_doc)
    
    # Also update the case summary to show we have notes
    await db.cases.update_one(
        {"case_id": case_id},
        {"$set": {"has_qualitative_notes": True, "updated_at": datetime.utcnow()}}
    )

    return {"status": "success", "adjustment": adjustment}

@router.get("/{case_id}/notes")
async def get_qualitative_notes(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    cursor = db.qualitative_notes.find({"case_id": case_id}).sort("created_at", -1)
    notes = await cursor.to_list(length=100)
    for n in notes:
        n["_id"] = str(n["_id"])
    return {"notes": notes}

@router.delete("/{case_id}/notes/{note_id}")
async def delete_qualitative_note(
    case_id: str,
    note_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    from bson import ObjectId
    db = get_database()
    res = await db.qualitative_notes.delete_one({"_id": ObjectId(note_id), "case_id": case_id, "user_id": current_user.id})
    if res.deleted_count:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Note not found")
