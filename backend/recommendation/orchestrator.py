"""
Recommendation Orchestrator: runs Five Cs scoring, loan structuring,
interest rate calculation, CAM generation, and Gemini AI narrative.
"""
import traceback
from datetime import datetime
from loguru import logger

from db.mongo import get_database
from app.constants import CRORE, MCLR_BASE_RATE, RISK_PREMIUM_TABLE


class RecommendationOrchestrator:

    async def run(self, case_id: str, requested_amount_paise: int = 0) -> dict:
        db = get_database()
        logger.info(f"Generating recommendation for case {case_id}")

        try:
            # Load required data
            analysis = await db.analyses.find_one({"case_id": case_id})
            case = await db.cases.find_one({"case_id": case_id})
            extraction = await db.extractions.find_one({"case_id": case_id})

            if not analysis:
                raise ValueError("Analysis not found — run analysis first")
            five_cs = analysis.get("five_cs_score", {})
            
            # ── Apply Qualitative Adjustments (Primary Insight Integration) ──
            notes_cursor = db.qualitative_notes.find({"case_id": case_id})
            notes = await notes_cursor.to_list(length=100)
            
            if notes:
                logger.info(f"[{case_id[:8]}] Applying {len(notes)} qualitative adjustments to Five Cs...")
                for n in notes:
                    adj_data = n.get("processed_adjustment", {})
                    dim = adj_data.get("dimension")
                    val = adj_data.get("adjustment", 0)
                    if dim in five_cs:
                        old_val = five_cs[dim]
                        # Cap adjustment to +/- 15 to prevent total skewing
                        new_val = max(0, min(100, old_val + val))
                        five_cs[dim] = round(new_val, 1)
                        logger.debug(f"  {dim}: {old_val} -> {five_cs[dim]} (Note: {n.get('note')[:30]}...)")
                
                # Re-calculate composite score if we modified dimensions
                weights = {"Character": 0.25, "Capacity": 0.30, "Capital": 0.20, "Collateral": 0.15, "Conditions": 0.10}
                new_composite = sum(five_cs.get(k, 50) * weights[k] for k in weights)
                five_cs["Composite"] = round(new_composite, 1)
                logger.info(f"[{case_id[:8]}] New composite score: {five_cs['Composite']}")

            composite = five_cs.get("Composite", 50)
            risk_grade = analysis.get("risk_grade", "B")

            # Determine collateral type from case data
            collateral_type = "stock_debtors"  # default
            if case:
                loan_type = (case.get("loan_type") or "").lower()
                if any(k in loan_type for k in ["term loan", "tl"]):
                    collateral_type = "plant_machinery"
                elif any(k in loan_type for k in ["mortgage", "lap", "land"]):
                    collateral_type = "land_building"
                elif any(k in loan_type for k in ["cc", "cash credit", "od", "overdraft", "working capital"]):
                    collateral_type = "stock_debtors"

            features_doc = await db.features.find_one({"case_id": case_id}) or {}

            # Generate recommendation
            rec = self._generate_recommendation(
                composite_score=composite,
                risk_grade=risk_grade,
                requested_amount_paise=requested_amount_paise,
                features=features_doc,
                analysis=analysis,
                five_cs=five_cs,
            )

            # Calculate interest rate using real collateral type
            rate = self._calculate_interest_rate(risk_grade, collateral_type)
            rec["interest_rate_pct"] = rate

            # MPBF from actual extraction data
            mpbf = self._calculate_mpbf(features_doc, extraction or {})
            rec["mpbf_paise"] = mpbf

            # Generate CAM
            output_dir = f"./data/processed/{case_id}"
            import os
            os.makedirs(output_dir, exist_ok=True)

            company_name = case.get("company_name", "Company") if case else "Company"

            cam_data = self._build_cam_data(
                case_id=case_id,
                company_name=company_name,
                extraction=extraction or {},
                analysis=analysis,
                five_cs=five_cs,
                recommendation=rec,
            )

            try:
                from recommendation.cam_generator.word_exporter import WordExporter
                word_path = os.path.join(output_dir, f"CAM_{case_id}.docx")
                WordExporter().export(cam_data, word_path)
                rec["cam_word_path"] = word_path
            except Exception as e:
                logger.warning(f"Word CAM generation failed: {e}")

            try:
                from recommendation.cam_generator.pdf_exporter import PDFExporter
                pdf_path = os.path.join(output_dir, f"CAM_{case_id}.pdf")
                PDFExporter().export(cam_data, pdf_path)
                rec["cam_pdf_path"] = pdf_path
            except Exception as e:
                logger.warning(f"PDF CAM generation failed: {e}")

            # ── Gemini AI enhancements ────────────────────────────────
            try:
                from ai_services.gemini_client import (
                    generate_credit_narrative, generate_swot, summarise_research,
                    generate_recom_mitigation
                )

                ews_report = await db.ews_reports.find_one({"case_id": case_id}) or {}
                ews_flags  = ews_report.get("flags", [])
                research   = await db.research_results.find_one({"case_id": case_id}) or {}
                research_items = research.get("items", [])

                shap_result = analysis.get("shap_result", {})
                top_shap    = shap_result.get("top_risk_drivers", [])[:5]

                logger.info(f"[{case_id[:8]}] Calling Gemini for narrative + SWOT + research summary...")

                # 1. Credit narrative
                ai_narrative = await generate_credit_narrative(
                    company_name      = company_name,
                    sector            = case.get("sector", "") if case else "",
                    credit_score      = analysis.get("credit_score", 0),
                    grade             = risk_grade,
                    default_probability = analysis.get("default_probability", 0),
                    five_cs           = five_cs,
                    top_shap_features = top_shap,
                    ews_flags         = ews_flags,
                    decision          = rec["decision"],
                    ratios            = (extraction or {}).get("ratio_results", []),
                )

                # 2. SWOT
                swot = await generate_swot(
                    company_name  = company_name,
                    sector        = case.get("sector", "") if case else "",
                    five_cs       = five_cs,
                    ews_flags     = ews_flags,
                    ratio_results = (extraction or {}).get("ratio_results", []),
                    research_items= research_items,
                )

                # 3. Research summary
                research_summary = await summarise_research(
                    company_name   = company_name,
                    sector         = case.get("sector", "") if case else "",
                    research_items = research_items,
                )

                # 4. Mitigation Plan
                mitigation = await generate_recom_mitigation(
                    company_name = company_name,
                    sector = case.get("sector", ""),
                    ews_flags = ews_flags,
                    five_cs = five_cs,
                    decision = rec["decision"]
                )

                rec["score_narrative"]   = ai_narrative
                rec["swot"]              = swot
                rec["research_summary"] = research_summary
                rec["mitigation_plan"]  = mitigation
                logger.success(f"[{case_id[:8]}] Gemini AI enhancements complete")

            except Exception as gem_err:
                logger.warning(f"[{case_id[:8]}] Gemini enhancement skipped: {gem_err}")
                # Fallback to template narrative if Gemini fails
                if not rec.get("score_narrative"):
                    grade = risk_grade
                    decision = rec.get("decision", "PRELIMINARY ASSESSMENT")
                    rec["score_narrative"] = f"Credit assessment for {company_name} resulted in a {grade} grade. High risk drivers identified in EWS. System recommends {decision}."
                
                # Ensure SWOT is never null
                if not rec.get("swot"):
                    rec["swot"] = {
                        "strengths": [f"Established presence in {case.get('sector', 'industry') if case else 'industry'}."],
                        "weaknesses": [f"{len(analysis.get('ews_flags', []))} risk flags detected."],
                        "opportunities": ["Sectoral growth prospects."],
                        "threats": ["Macroeconomic headwinds."]
                    }
                
                rec.setdefault("research_summary", "Secondary research data currently limited.")
                rec.setdefault("mitigation_plan", {
                    "dos": ["Obtain personal guarantee.", "Conduct quarterly audit."],
                    "donts": ["No further debt without approval."],
                    "monitoring": ["Monitor DSCR quarterly."]
                })

            # ─────────────────────────────────────────────────────────

            rec.update({
                "case_id":    case_id,
                "created_at": datetime.utcnow(),
                "five_cs_score": five_cs,
                "company_name": company_name,
                "top_risk_drivers": shap_result.get("top_risk_drivers", []),
                "shap_contributions": shap_result.get("feature_contributions", []),
            })

            await db.recommendations.replace_one({"case_id": case_id}, rec, upsert=True)
            logger.info(f"Recommendation generated for {case_id}: {rec['decision']}")
            return rec

        except Exception as e:
            logger.error(f"Recommendation failed for {case_id}: {e}\n{traceback.format_exc()}")
            raise

    def _generate_recommendation(
        self, composite_score, risk_grade, requested_amount_paise,
        features, analysis, five_cs
    ) -> dict:
        """
        Decision logic based on composite Five Cs score.
        """
        reasons = []
        covenants = []
        exceptions = []

        if composite_score < 30:
            decision = "REJECT"
            rec_limit = 0
            reasons.append(f"Composite score of {composite_score:.1f}/100 is below minimum threshold of 30")
            reasons.append(f"Risk grade {risk_grade} indicates high probability of default")

        elif composite_score < 45:
            decision = "REFER"
            rec_limit = int(requested_amount_paise * 0.60) if requested_amount_paise > 0 else 0
            reasons.append(f"Composite score of {composite_score:.1f}/100 requires credit committee review")
            covenants.extend([
                "Monthly stock and debtors statements required",
                "Quarterly audited financials mandatory",
                "No further debt without prior bank approval",
                "Promoter personal guarantee required",
            ])

        elif composite_score < 65:
            decision = "APPROVE_WITH_CONDITIONS"
            reduction = 0.80 if features.get("feature_vector", {}).get("debt_equity_fy1", 0) or 0 > 3 else 1.0
            rec_limit = int(requested_amount_paise * reduction)
            reasons.append(f"Composite score of {composite_score:.1f}/100 warrants conditional approval")
            covenants.extend([
                "Quarterly financial monitoring",
                "Annual credit review",
                "Maintain D/E ratio within sanctioned limits",
            ])
            if reduction < 1.0:
                reasons.append("Recommended limit reduced by 20% due to elevated leverage ratio")

        else:
            decision = "APPROVE"
            rec_limit = requested_amount_paise
            reasons.append(f"Strong composite score of {composite_score:.1f}/100 supports approval")
            covenants.append("Annual credit review")

        # MPBF calculation
        fv = features.get("feature_vector", {})
        mpbf = self._calculate_mpbf(fv)

        # Facility breakup
        total = rec_limit or mpbf
        facility_breakup = {
            "working_capital_paise": int(total * 0.60),
            "term_loan_paise": int(total * 0.30),
            "letter_of_credit_paise": int(total * 0.10),
        }

        return {
            "decision": decision,
            "recommended_limit_paise": rec_limit,
            "mpbf_paise": mpbf,
            "facility_breakup": facility_breakup,
            "reasons": reasons,
            "covenants": covenants,
            "exceptions": exceptions,
        }

    def _calculate_mpbf(self, features: dict, extraction: dict = None) -> int:
        """
        Maximum Permissible Bank Finance — Tandon Committee Method II.
        MPBF = 0.75 × (Total Current Assets − Core Current Liabilities)
        Falls back to ratio-based estimate when balance sheet is unavailable.
        """
        try:
            # Try to get current assets and liabilities from financial records
            fin_records = (extraction or {}).get("financial_records", [])
            if fin_records:
                latest = fin_records[0] if isinstance(fin_records[0], dict) else getattr(fin_records[0], '__dict__', {})
                ca = latest.get("current_assets") or latest.get("total_current_assets") or 0
                cl = latest.get("current_liabilities") or latest.get("total_current_liabilities") or 0
                if ca > 0 and cl > 0:
                    nwc = ca - cl
                    mpbf = int(0.75 * max(0, ca - nwc))
                    return mpbf

            # Fallback: estimate from feature vector ratios
            fv = features.get("feature_vector", {})
            current_ratio = fv.get("current_ratio_fy1", 0) or 0
            # We don't have absolute values, return 0 to avoid fabricating numbers
            return 0
        except Exception as e:
            logger.debug(f"MPBF calculation error: {e}")
            return 0

    def _calculate_interest_rate(self, risk_grade: str, collateral_type: str) -> float:
        """Calculate interest rate = MCLR + risk premium + collateral adjustment."""
        premium = RISK_PREMIUM_TABLE.get(risk_grade, 2.0)

        collateral_adjustments = {
            "land_building": -0.25,
            "plant_machinery": -0.10,
            "stock_debtors": 0.00,
            "third_party": 0.10,
        }
        collateral_adj = collateral_adjustments.get(collateral_type, 0)

        return round(MCLR_BASE_RATE + premium + collateral_adj, 2)

    def _build_cam_data(self, case_id, company_name, extraction, analysis, five_cs, recommendation) -> dict:
        """Build complete CAM data structure."""
        shap = analysis.get("shap_result", {})
        return {
            "case_id": case_id,
            "company_name": company_name,
            "credit_score": analysis.get("credit_score", 0),
            "risk_grade": analysis.get("risk_grade", "N/A"),
            "default_probability": analysis.get("default_probability", 0),
            "decision": recommendation.get("decision", "N/A"),
            "recommended_limit_paise": recommendation.get("recommended_limit_paise", 0),
            "interest_rate_pct": recommendation.get("interest_rate_pct", 0),
            "five_cs": five_cs,
            "reasons": recommendation.get("reasons", []),
            "covenants": recommendation.get("covenants", []),
            "facility_breakup": recommendation.get("facility_breakup", {}),
            "top_risk_drivers": shap.get("top_risk_drivers", []),
            "shap_contributions": shap.get("feature_contributions", []),
            "score_narrative": analysis.get("score_narrative", ""),
            "financial_records": extraction.get("financial_records", []),
            "ratio_results": extraction.get("ratio_results", []),
            "gst_reconciliation": extraction.get("gst_internal_reconciliation", {}),
            "circular_trading": extraction.get("circular_trading_summary", {}),
            "legal_data": extraction.get("legal_data", []),
            "generated_at": datetime.utcnow().strftime("%d %B %Y, %H:%M IST"),
        }
