import networkx as nx
from typing import Optional
from loguru import logger
from app.constants import CRORE


class TransactionGraphBuilder:
    """Builds a directed graph of GST transactions for circular trading detection."""

    def build(
        self,
        gstr1_buyers: list,       # [{gstin, monthly_value}]
        gstr2a_suppliers: list,   # [{gstin, monthly_value}]
        related_parties: list,    # GSTINs from annual report
        subject_gstin: str = "",
    ) -> nx.DiGraph:
        G = nx.DiGraph()

        # Add subject company as center node
        if subject_gstin:
            G.add_node(subject_gstin, node_type="subject", label="Subject Company")

        # Add buyer edges (company → buyer)
        for buyer in gstr1_buyers:
            gstin = buyer.get("gstin", "")
            value = buyer.get("value", buyer.get("monthly_value", 0))
            if not gstin:
                continue
            node_type = "related_party" if gstin in related_parties else "buyer"
            G.add_node(gstin, node_type=node_type)
            if subject_gstin:
                G.add_edge(subject_gstin, gstin, weight=value, transaction_type="sale")

        # Add supplier edges (supplier → company)
        for supplier in gstr2a_suppliers:
            gstin = supplier.get("gstin", "")
            value = supplier.get("value", supplier.get("monthly_value", 0))
            if not gstin:
                continue
            node_type = "related_party" if gstin in related_parties else "supplier"
            if gstin not in G.nodes:
                G.add_node(gstin, node_type=node_type)
            if subject_gstin:
                G.add_edge(gstin, subject_gstin, weight=value, transaction_type="purchase")

        return G


class CycleDetector:
    """Detects circular trading cycles in the transaction graph."""

    def detect(
        self,
        graph: nx.DiGraph,
        subject_gstin: str,
        annual_turnover_paise: int,
    ) -> list:
        """
        Uses networkx.simple_cycles() for DFS cycle detection.
        Only returns cycles where circulation ratio > 5% of turnover.
        """
        cycles = []
        try:
            all_cycles = list(nx.simple_cycles(graph))
        except Exception as e:
            logger.warning(f"Cycle detection failed: {e}")
            return cycles

        for cycle_path in all_cycles:
            if len(cycle_path) < 2:
                continue

            # Calculate total value rotating through cycle
            cycle_value = float('inf')
            for i in range(len(cycle_path)):
                src = cycle_path[i]
                dst = cycle_path[(i + 1) % len(cycle_path)]
                edge_data = graph.get_edge_data(src, dst, {})
                weight = edge_data.get("weight", 0)
                cycle_value = min(cycle_value, weight)

            if cycle_value == float('inf'):
                cycle_value = 0

            circulation_ratio = cycle_value / annual_turnover_paise if annual_turnover_paise > 0 else 0

            if circulation_ratio > 0.05:  # > 5% of turnover
                cycles.append({
                    "path": cycle_path,
                    "total_value_paise": int(cycle_value),
                    "value_circulation_ratio": round(circulation_ratio, 3),
                    "cycle_includes_subject": subject_gstin in cycle_path,
                    "entity_count": len(cycle_path),
                    "is_high_value": circulation_ratio > 0.10,
                })

        return cycles

    def get_summary(self, cycles: list, annual_turnover_paise: int) -> dict:
        if not cycles:
            return {
                "total_cycles_detected": 0,
                "high_value_cycles": 0,
                "total_value_at_risk_paise": 0,
                "risk_level": "LOW",
                "narrative": "No circular trading patterns detected in transaction graph analysis.",
            }

        total_value = sum(c["total_value_paise"] for c in cycles)
        high_value = sum(1 for c in cycles if c["is_high_value"])
        entity_count = len(set(n for c in cycles for n in c["path"]))
        cycle_cr = total_value / (CRORE * 100)
        turnover_cr = annual_turnover_paise / (CRORE * 100)
        circulation_pct = (total_value / annual_turnover_paise * 100) if annual_turnover_paise > 0 else 0

        risk = "LOW"
        if len(cycles) >= 3 or high_value >= 2:
            risk = "CRITICAL"
        elif len(cycles) >= 2 or high_value >= 1:
            risk = "HIGH"
        elif len(cycles) == 1:
            risk = "MEDIUM"

        narrative = (
            f"Transaction graph analysis identified {len(cycles)} circular invoice cycle(s) "
            f"involving {entity_count} entities. Total value rotating through these cycles: "
            f"₹{cycle_cr:.2f} Cr, representing {circulation_pct:.1f}% of declared annual "
            f"turnover of ₹{turnover_cr:.2f} Cr."
        )

        return {
            "total_cycles_detected": len(cycles),
            "high_value_cycles": high_value,
            "total_value_at_risk_paise": total_value,
            "entity_count": entity_count,
            "risk_level": risk,
            "narrative": narrative,
        }


class ShellCompanyScorer:
    """Scores counterparty entities for shell company characteristics."""

    SCORE_RULES = {
        "age_under_2_years": 2,
        "min_authorized_capital": 2,       # authorized cap = ₹1 lakh
        "same_address_multiple": 3,
        "director_multiple_registrations": 2,
        "no_digital_footprint": 1,
        "single_transaction_entity": 2,
        "round_number_transactions": 1,
    }

    def score(self, gstin_info: dict) -> dict:
        """
        Checks each rule, sums score.
        Score >= 5: SHELL_COMPANY_SUSPECTED
        """
        total = 0
        triggered = []

        if gstin_info.get("company_age_years", 10) < 2:
            total += self.SCORE_RULES["age_under_2_years"]
            triggered.append("age_under_2_years")

        if gstin_info.get("authorized_capital_rupees", 0) <= 100000:
            total += self.SCORE_RULES["min_authorized_capital"]
            triggered.append("min_authorized_capital")

        if gstin_info.get("same_address_count", 0) > 2:
            total += self.SCORE_RULES["same_address_multiple"]
            triggered.append("same_address_multiple")

        if gstin_info.get("director_other_company_count", 0) > 5:
            total += self.SCORE_RULES["director_multiple_registrations"]
            triggered.append("director_multiple_registrations")

        if not gstin_info.get("has_digital_footprint", True):
            total += self.SCORE_RULES["no_digital_footprint"]
            triggered.append("no_digital_footprint")

        if gstin_info.get("transaction_count", 10) == 1:
            total += self.SCORE_RULES["single_transaction_entity"]
            triggered.append("single_transaction_entity")

        classification = "SHELL_COMPANY_SUSPECTED" if total >= 5 else (
            "HIGH_RISK" if total >= 3 else "LOW_RISK"
        )

        return {
            "gstin": gstin_info.get("gstin", ""),
            "total_score": total,
            "rules_triggered": triggered,
            "classification": classification,
        }
