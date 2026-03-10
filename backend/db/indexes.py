from loguru import logger
from db.mongo import get_database


async def create_indexes():
    db = get_database()
    if db is None:
        return

    # users
    await db.users.create_index("email", unique=True)

    # cases
    await db.cases.create_index("user_id")
    await db.cases.create_index("company_name")
    await db.cases.create_index("created_at")
    await db.cases.create_index("case_id", unique=True)

    # extractions
    await db.extractions.create_index("case_id", unique=True)

    # audit_trails
    await db.audit_trails.create_index("case_id")

    # analyses
    await db.analyses.create_index("case_id")

    # recommendations
    await db.recommendations.create_index("case_id")

    # features
    await db.features.create_index("case_id")

    # ews_reports
    await db.ews_reports.create_index("case_id")

    logger.info("MongoDB indexes created.")
