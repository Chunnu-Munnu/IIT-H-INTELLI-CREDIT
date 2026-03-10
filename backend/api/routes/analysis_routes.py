from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from auth.service import get_current_user
from auth.models import UserResponse
from db.mongo import get_database

router = APIRouter()


@router.post("/{case_id}/analyze")
async def run_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    case = await db.cases.find_one({"case_id": case_id, "user_id": current_user.id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    from analysis.orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    background_tasks.add_task(orchestrator.run, case_id)
    return {"message": "Analysis started", "case_id": case_id}


@router.get("/{case_id}/analysis")
async def get_analysis(
    case_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    db = get_database()
    analysis = await db.analyses.find_one({"case_id": case_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not yet available")
    analysis["_id"] = str(analysis["_id"])
    return analysis


@router.post("/{case_id}/primary-input")
async def submit_primary_input(
    case_id: str,
    payload: dict,
    current_user: UserResponse = Depends(get_current_user),
):
    """Accept qualitative credit officer notes and adjust the analysis score."""
    db = get_database()
    from research_agent.primary_input_handler import PrimaryInputHandler
    handler = PrimaryInputHandler()
    note = payload.get("note", "")
    adjustment = handler.process_qualitative_note(note, case_id)

    # Store the note
    await db.primary_inputs.update_one(
        {"case_id": case_id},
        {"$push": {"notes": {"note": note, "adjustment": adjustment.dict()}}},
        upsert=True,
    )
    return {"adjustment": adjustment.dict(), "message": "Note processed and score adjusted"}
