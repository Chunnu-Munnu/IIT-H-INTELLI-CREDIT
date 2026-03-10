from models.risk import EWSFlag, EWSReport, RiskLevel
from app.constants import EWS_FLAGS, CRORE


class EWSEngine:
    """
    Early Warning Signal Engine.
    Evaluates all 15 EWS flags from constants and produces EWSReport.
    """

    FLAG_SEVERITY = {
        "AUDITOR_QUALIFIED_OPINION": (RiskLevel.HIGH, 15, "Character"),
        "GOING_CONCERN_DOUBT": (RiskLevel.CRITICAL, 25, "Character"),
        "ITC_INFLATION_FRAUD_SUSPECTED": (RiskLevel.CRITICAL, 20, "Conditions"),
        "CIRCULAR_TRADING_DETECTED": (RiskLevel.HIGH, 15, "Conditions"),
        "UNDISCLOSED_BORROWINGS_FOUND": (RiskLevel.CRITICAL, 20, "Capital"),
        "REVENUE_INFLATION_HIGH": (RiskLevel.HIGH, 15, "Conditions"),
        "WINDOW_DRESSING_SUSPECTED": (RiskLevel.MEDIUM, 8, "Capacity"),
        "NACH_BOUNCE_PATTERN": (RiskLevel.HIGH, 12, "Capacity"),
        "DRT_CASE_ACTIVE": (RiskLevel.CRITICAL, 20, "Character"),
        "DIRECTOR_CIRP_LINKED": (RiskLevel.CRITICAL, 18, "Character"),
        "RATING_DOWNGRADED": (RiskLevel.HIGH, 10, "Character"),
        "GST_FILING_LAPSED": (RiskLevel.HIGH, 12, "Conditions"),
        "MCA_COMPLIANCE_LAPSED": (RiskLevel.MEDIUM, 8, "Character"),
        "BALANCE_SHEET_MISMATCH": (RiskLevel.HIGH, 15, "Capital"),
        "TURNOVER_SUPPRESSION_GST": (RiskLevel.HIGH, 15, "Conditions"),
    }

    def generate_report(
        self,
        case_id: str,
        gst_bank_result: dict = None,
        gst_internal_result: dict = None,
        circular_trading_summary: dict = None,
        window_dressing_result: dict = None,
        mca_result: dict = None,
        risk_signals: list = None,
        bank_analysis=None,
        rating_data: dict = None,
        legal_data: list = None,
        extraction_data: dict = None,
    ) -> EWSReport:
        flags = []
        risk_signals = risk_signals or []
        legal_data = legal_data or []

        for flag_name in EWS_FLAGS:
            severity, deduction, five_c = self.FLAG_SEVERITY.get(
                flag_name, (RiskLevel.MEDIUM, 5, "Conditions")
            )
            triggered = False
            evidence = ""
            source_docs = []

            if flag_name == "AUDITOR_QUALIFIED_OPINION":
                for sig in risk_signals:
                    if sig.get("signal_type") == "AUDITOR_QUALIFICATION":
                        triggered = True
                        evidence = sig.get("context_text", "Qualified auditor opinion detected.")
                        source_docs = [sig.get("source_document", "")]
                        break

            elif flag_name == "GOING_CONCERN_DOUBT":
                for sig in risk_signals:
                    if sig.get("signal_type") == "GOING_CONCERN":
                        triggered = True
                        evidence = sig.get("context_text", "Going concern doubt expressed by auditors.")
                        source_docs = [sig.get("source_document", "")]
                        break

            elif flag_name == "ITC_INFLATION_FRAUD_SUSPECTED":
                if gst_internal_result and gst_internal_result.get("itc_inflation_flag"):
                    triggered = True
                    evidence = gst_internal_result.get("itc_narrative", "ITC excess claim detected.")
                    source_docs = ["GSTR-3B", "GSTR-2A"]

            elif flag_name == "CIRCULAR_TRADING_DETECTED":
                if circular_trading_summary and circular_trading_summary.get("total_cycles_detected", 0) > 0:
                    triggered = True
                    evidence = circular_trading_summary.get("narrative", "Circular trading detected.")
                    source_docs = ["GSTR-1", "GSTR-2A"]

            elif flag_name == "UNDISCLOSED_BORROWINGS_FOUND":
                if mca_result and mca_result.get("undisclosed_paise", 0) > 50 * CRORE * 100:
                    triggered = True
                    evidence = mca_result.get("narrative", "Undisclosed borrowings found in MCA registry.")
                    source_docs = ["MCA Charge Registry", "Balance Sheet"]

            elif flag_name == "REVENUE_INFLATION_HIGH":
                if gst_bank_result and gst_bank_result.get("flag_triggered"):
                    triggered = True
                    evidence = gst_bank_result.get("narrative", "Revenue inflation detected.")
                    source_docs = ["GST Returns", "Bank Statement"]

            elif flag_name == "WINDOW_DRESSING_SUSPECTED":
                if window_dressing_result and window_dressing_result.get("flag_triggered"):
                    triggered = True
                    evidence = window_dressing_result.get("narrative", "Window dressing pattern detected.")
                    source_docs = ["Bank Statement"]

            elif flag_name == "NACH_BOUNCE_PATTERN":
                if bank_analysis and hasattr(bank_analysis, "nach_bounce_count"):
                    if bank_analysis.nach_bounce_count >= 2:
                        triggered = True
                        evidence = f"{bank_analysis.nach_bounce_count} NACH bounces detected in bank statement."
                        source_docs = ["Bank Statement"]

            elif flag_name == "DRT_CASE_ACTIVE":
                for legal in legal_data:
                    if legal.get("case_type") == "DRT":
                        triggered = True
                        evidence = f"Active DRT case: {legal.get('case_number', 'Unknown')}."
                        source_docs = ["Legal Notice", "DRT Filing"]
                        break

            elif flag_name == "DIRECTOR_CIRP_LINKED":
                for sig in risk_signals:
                    if "cirp" in sig.get("keyword_matched", "").lower() or "director" in sig.get("context_text", "").lower():
                        triggered = True
                        evidence = "Director linked to CIRP proceedings."
                        source_docs = ["MCA Filings"]
                        break

            elif flag_name == "RATING_DOWNGRADED":
                if rating_data and rating_data.get("direction") == "downgrade":
                    triggered = True
                    evidence = f"Credit rating downgraded from {rating_data.get('previous_rating')} to {rating_data.get('current_rating')}."
                    source_docs = ["Rating Report"]

            elif flag_name == "GST_FILING_LAPSED":
                if gst_bank_result:
                    monthly = gst_bank_result.get("monthly_ratios", {})
                    if any(v is None for v in monthly.values()):
                        triggered = True
                        evidence = "GST filing gaps detected in monthly series."
                        source_docs = ["GSTR-3B"]

            elif flag_name == "MCA_COMPLIANCE_LAPSED":
                if mca_result and mca_result.get("compliance_lapsed"):
                    triggered = True
                    evidence = "MCA compliance filings are lapsed."
                    source_docs = ["MCA Company Master"]

            elif flag_name == "BALANCE_SHEET_MISMATCH":
                if extraction_data:
                    mismatch = extraction_data.get("balance_sheet_mismatch", False)
                    if mismatch:
                        triggered = True
                        evidence = "Balance sheet assets do not equal liabilities + equity."
                        source_docs = ["Financial Statements"]

            elif flag_name == "TURNOVER_SUPPRESSION_GST":
                if gst_internal_result and gst_internal_result.get("turnover_suppression_flag"):
                    triggered = True
                    evidence = gst_internal_result.get("turnover_narrative", "Turnover suppression detected.")
                    source_docs = ["GSTR-1", "GSTR-3B"]

            flags.append(EWSFlag(
                flag_name=flag_name,
                triggered=triggered,
                severity=severity,
                evidence_summary=evidence,
                five_c_impact=five_c,
                score_deduction=deduction if triggered else 0,
                source_documents=source_docs,
            ))

        total_deduction = sum(f.score_deduction for f in flags)
        triggered_count = sum(1 for f in flags if f.triggered)
        critical_count = sum(1 for f in flags if f.triggered and f.severity == RiskLevel.CRITICAL)
        high_count = sum(1 for f in flags if f.triggered and f.severity == RiskLevel.HIGH)

        if critical_count >= 2:
            overall_risk = RiskLevel.CRITICAL
        elif critical_count >= 1 or high_count >= 3:
            overall_risk = RiskLevel.HIGH
        elif high_count >= 1 or triggered_count >= 3:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        return EWSReport(
            case_id=case_id,
            flags=flags,
            total_score_deduction=min(100, total_deduction),
            overall_risk_classification=overall_risk,
            triggered_count=triggered_count,
            critical_count=critical_count,
            high_count=high_count,
        )
