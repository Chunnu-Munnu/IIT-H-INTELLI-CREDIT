from typing import Optional

from models.financial import FinancialRecord, RatioResult, FinancialPeriod
from datetime import date


def safe_div(numerator, denominator) -> Optional[float]:
    """Safe division returning None if denominator is zero or None."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


class RatioCalculator:
    """
    Calculates all financial ratios from FinancialRecord.
    All inputs in paise, outputs are floats (ratios are dimensionless).
    """

    def calculate(self, record: FinancialRecord) -> RatioResult:
        # Convert to dict if it's an object, or support both access patterns
        def val(attr, default=None):
            if isinstance(record, dict):
                return record.get(attr, default)
            return getattr(record, attr, default)

        period_val = val("period", "Unknown")
        
        # Ensure 'period' is a proper FinancialPeriod object for Pydantic
        if isinstance(period_val, FinancialPeriod):
            period = period_val
        elif isinstance(period_val, dict):
            period = FinancialPeriod(
                fy_label=period_val.get("fy_label") or period_val.get("label") or "Unknown",
                start_date=period_val.get("start_date") or date(2023, 4, 1),
                end_date=period_val.get("end_date") or date(2024, 3, 31)
            )
        else:
            period = FinancialPeriod(
                fy_label=str(period_val),
                start_date=date(2023, 4, 1),
                end_date=date(2024, 3, 31)
            )

        ratio = RatioResult(period=period)

        # Map fields (paise)
        current_assets = val("current_assets") or val("total_current_assets")
        current_liabilities = val("current_liabilities") or val("total_current_liabilities")
        inventory = val("inventory")
        total_debt = val("total_debt")
        net_worth = val("net_worth")
        ebitda = val("ebitda")
        finance_costs = val("finance_costs") or val("interest")
        pat = val("pat")
        depreciation = val("depreciation")
        long_term_debt = val("long_term_debt")
        revenue = val("revenue_from_ops") or val("revenue")
        ebit = val("ebit")
        total_assets = val("total_assets")
        debtors = val("debtors") or val("trade_receivables")
        inventory_val = val("inventory") # redundant but for clarity
        cogs = val("cogs") or val("cost_of_goods_sold")
        creditors = val("creditors") or val("trade_payables")

        # Liquidity ratios
        ratio.current_ratio = safe_div(current_assets, current_liabilities)
        if current_assets and inventory and current_liabilities:
            ratio.quick_ratio = safe_div(current_assets - inventory, current_liabilities)

        # Leverage ratios
        ratio.debt_equity = safe_div(total_debt, net_worth)
        if total_debt and current_liabilities and net_worth:
            total_outside_liabilities = (total_debt or 0) + (current_liabilities or 0)
            ratio.tol_tnw = safe_div(total_outside_liabilities, net_worth)

        # Coverage ratios
        if ebitda and finance_costs:
            ratio.interest_coverage = safe_div(ebitda, finance_costs)

        # DSCR = (PAT + Depreciation + Finance Costs) / (Annual Repayment + Finance Costs)
        if pat and depreciation and finance_costs:
            net_cash_accrual = (pat or 0) + (depreciation or 0) + (finance_costs or 0)
            # Approximate annual repayment as 20% of total debt (common assumption)
            repayment = (long_term_debt or 0) * 0.20
            debt_service = repayment + (finance_costs or 0)
            ratio.dscr = safe_div(net_cash_accrual, debt_service)

        # Profitability ratios
        ratio.pat_margin = safe_div(pat, revenue)
        ratio.ebitda_margin = safe_div(ebitda, revenue)

        # Return ratios
        if ebit and total_assets and current_liabilities:
            cap_employed = (total_assets or 0) - (current_liabilities or 0)
            ratio.roce = safe_div(ebit, cap_employed)
        ratio.roe = safe_div(pat, net_worth)

        # Working capital ratios (in days)
        if revenue:
            daily_sales = revenue / 365
            ratio.debtor_days = safe_div(debtors, daily_sales)
            ratio.inventory_days = safe_div(inventory, daily_sales)

        if cogs:
            daily_purchases = cogs / 365
            ratio.creditor_days = safe_div(creditors, daily_purchases)

        # Asset turnover
        ratio.asset_turnover = safe_div(revenue, total_assets)

        # Confidence: reduce for every missing key field
        key_fields = ["revenue_from_ops", "pat", "total_assets", "total_debt", "net_worth"]
        present_count = sum(1 for f in key_fields if val(f) is not None)
        
        ext_conf = float(val("extraction_confidence", 0.8) or 0.8)
        ratio.confidence = (float(present_count) / float(len(key_fields))) * ext_conf

        return ratio
