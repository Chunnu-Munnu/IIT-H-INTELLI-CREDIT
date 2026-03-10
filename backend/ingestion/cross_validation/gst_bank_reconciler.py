from typing import Optional
from loguru import logger
from app.constants import LAKH, CRORE


class GSTBankReconciler:
    """Cross-validates GST declared turnover against bank deposits."""

    def reconcile(
        self,
        gst_monthly_series: dict,    # YYYY-MM -> paise
        bank_monthly_series: dict,   # YYYY-MM -> paise
        threshold: float = 1.4
    ) -> dict:
        """
        For each overlapping month: ratio = gst_turnover / bank_deposits
        Flags REVENUE_INFLATION if overall_ratio > threshold
        """
        common_months = set(gst_monthly_series.keys()) & set(bank_monthly_series.keys())

        if not common_months:
            return {
                "overall_ratio": None,
                "monthly_ratios": {},
                "worst_months": [],
                "flag_triggered": False,
                "narrative": "Insufficient data to cross-validate GST and bank turnover.",
                "gst_annual_paise": sum(gst_monthly_series.values()),
                "bank_annual_paise": sum(bank_monthly_series.values()),
                "risk": "LOW",
            }

        gst_total = sum(gst_monthly_series.get(m, 0) for m in common_months)
        bank_total = sum(bank_monthly_series.get(m, 0) for m in common_months)

        if bank_total == 0:
            return {
                "overall_ratio": None,
                "flag_triggered": False,
                "narrative": "Bank deposits data unavailable for reconciliation.",
                "risk": "MEDIUM",
            }

        overall_ratio = gst_total / bank_total

        # Monthly ratios
        monthly_ratios = {}
        for m in sorted(common_months):
            g = gst_monthly_series.get(m, 0)
            b = bank_monthly_series.get(m, 0)
            monthly_ratios[m] = round(g / b, 2) if b > 0 else None

        # Worst 3 months
        sorted_ratios = sorted(
            [(m, r) for m, r in monthly_ratios.items() if r is not None],
            key=lambda x: x[1] if x[1] else 0,
            reverse=True
        )
        worst_3 = sorted_ratios[:3]

        flag_triggered = overall_ratio > threshold

        gst_cr = gst_total / (CRORE * 100)
        bank_cr = bank_total / (CRORE * 100)

        narrative = (
            f"GST declared turnover of ₹{gst_cr:.2f} Cr for the period was cross-referenced "
            f"against bank deposits of ₹{bank_cr:.2f} Cr for the same period, yielding "
            f"an inflation ratio of {overall_ratio:.1f}x against threshold of {threshold}x. "
        )
        if flag_triggered:
            peak = worst_3[0] if worst_3 else None
            months_str = ", ".join([f"{m} ({r}x)" for m, r in worst_3])
            narrative += (
                f"REVENUE INFLATION FLAG TRIGGERED. Peak divergence in months: {months_str}. "
                f"This indicates GST-declared turnover significantly exceeds bank-verifiable deposits, "
                f"a common indicator of revenue inflation or circular trading."
            )
            risk = "HIGH" if overall_ratio > 2.0 else "MEDIUM"
        else:
            narrative += f"GST-bank reconciliation is within acceptable range."
            risk = "LOW"

        return {
            "overall_ratio": round(overall_ratio, 3),
            "monthly_ratios": monthly_ratios,
            "worst_months": worst_3,
            "flag_triggered": flag_triggered,
            "narrative": narrative,
            "gst_annual_paise": gst_total,
            "bank_annual_paise": bank_total,
            "risk": risk if flag_triggered else "LOW",
        }


class GSTInternalReconciler:
    """Reconciles GSTR-1 vs GSTR-3B vs GSTR-2A vs GSTR-9."""

    def reconcile(
        self,
        gstr1,
        gstr3b,
        gstr2a,
        gstr9=None,
        itc_threshold: float = 1.05,
        turnover_threshold_paise: int = 5 * LAKH * 100,  # 5 lakh in paise
    ) -> dict:
        result = {
            "turnover_suppression_flag": False,
            "itc_inflation_flag": False,
            "annual_reconciliation_gap_flag": False,
            "gstr1_vs_3b_delta_paise": 0,
            "itc_excess_claim_paise": 0,
            "gstr9_vs_3b_delta_paise": None,
            "itc_narrative": "",
            "turnover_narrative": "",
            "overall_gst_risk": "LOW",
        }

        # CHECK 1: GSTR-1 vs GSTR-3B Turnover
        if gstr1 and gstr3b:
            delta = gstr1.annual_turnover_paise - gstr3b.annual_outward_paise
            result["gstr1_vs_3b_delta_paise"] = delta
            abs_delta = abs(delta)
            total = gstr1.annual_turnover_paise
            relative_delta = abs_delta / total if total > 0 else 0

            if abs_delta > turnover_threshold_paise and relative_delta > 0.02:
                result["turnover_suppression_flag"] = True
                g1_cr = gstr1.annual_turnover_paise / (CRORE * 100)
                g3b_cr = gstr3b.annual_outward_paise / (CRORE * 100)
                delta_cr = delta / (CRORE * 100)
                result["turnover_narrative"] = (
                    f"GSTR-1 declares annual turnover of ₹{g1_cr:.2f} Cr, while GSTR-3B "
                    f"reports only ₹{g3b_cr:.2f} Cr — a mismatch of ₹{delta_cr:.2f} Cr "
                    f"({relative_delta*100:.1f}%). This triggers the TURNOVER_SUPPRESSION_GST flag."
                )
            else:
                result["turnover_narrative"] = (
                    f"GSTR-1 and GSTR-3B turnover figures are in acceptable alignment."
                )

        # CHECK 2: ITC INFLATION (Critical Fraud Check)
        if gstr3b and gstr2a:
            itc_eligible_with_buffer = gstr2a.total_itc_eligible_paise * itc_threshold
            itc_excess = gstr3b.total_itc_claimed_paise - itc_eligible_with_buffer
            result["itc_excess_claim_paise"] = max(0, int(itc_excess))

            if itc_excess > 0:
                result["itc_inflation_flag"] = True
                claimed_cr = gstr3b.total_itc_claimed_paise / (CRORE * 100)
                eligible_cr = gstr2a.total_itc_eligible_paise / (CRORE * 100)
                excess_cr = itc_excess / (CRORE * 100)
                contingent = excess_cr * 1.18  # 18% interest
                result["itc_narrative"] = (
                    f"Company claimed ITC of ₹{claimed_cr:.2f} Cr in GSTR-3B versus "
                    f"eligible ITC of ₹{eligible_cr:.2f} Cr auto-populated in GSTR-2A, "
                    f"resulting in excess claim of ₹{excess_cr:.2f} Cr. "
                    f"Under Section 16 of the CGST Act, this excess may be reversed "
                    f"with 18% interest + penalty of up to 100% of the excess claim. "
                    f"Estimated contingent tax liability: ₹{contingent:.2f} Cr."
                )
            else:
                result["itc_narrative"] = "ITC claimed is within eligible limits per GSTR-2A."

        # CHECK 3: GSTR-9 Annual Reconciliation
        if gstr9 and gstr3b:
            gstr3b_sum = gstr3b.annual_outward_paise
            delta_9 = abs(gstr9.annual_turnover_paise - gstr3b_sum)
            result["gstr9_vs_3b_delta_paise"] = delta_9
            if delta_9 > turnover_threshold_paise:
                result["annual_reconciliation_gap_flag"] = True

        # Monthly entries for frontend
        all_months = set()
        if gstr1: all_months.update(gstr1.monthly_turnover.keys())
        if gstr3b: all_months.update(gstr3b.monthly_data.keys())
        if gstr2a: all_months.update(gstr2a.monthly_itc.keys())

        monthly_entries = []
        for m in sorted(all_months):
            entry = {
                "month": m,
                "gstin": (gstr1.gstin if gstr1 else gstr3b.gstin if gstr3b else gstr2a.gstin if gstr2a else ""),
                "outward_taxable": (gstr1.monthly_turnover.get(m, 0) if gstr1 else gstr3b.monthly_data.get(m, {}).get("outward", 0) if gstr3b else 0),
                "itc_claimed": (gstr3b.monthly_data.get(m, {}).get("itc", 0) if gstr3b else 0),
                "itc_eligible": (gstr2a.monthly_itc.get(m, 0) if gstr2a else 0),
                "tax_paid": 0,
                "filing_status": "filed"
            }
            monthly_entries.append(entry)
        
        result["monthly_entries"] = monthly_entries

        # Overall risk
        flags = [
            result["turnover_suppression_flag"],
            result["itc_inflation_flag"],
            result["annual_reconciliation_gap_flag"],
        ]
        triggered = sum(flags)
        if triggered >= 2:
            result["overall_gst_risk"] = "CRITICAL"
        elif triggered == 1:
            result["overall_gst_risk"] = "HIGH"
        else:
            result["overall_gst_risk"] = "LOW"

        return result
