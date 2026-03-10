"""
risk_propagation_engine.py
PageRank-style risk propagation through the corporate graph.
"""
import networkx as nx
import numpy as np
from loguru import logger


class RiskPropagationEngine:

    def __init__(self, G: nx.DiGraph):
        self.G = G

    def compute_pagerank_risk(self, alpha: float = 0.85) -> dict:
        """
        Edge-weighted PageRank on undirected version of graph.
        Nodes with more high-value connections get higher risk scores.
        """
        if self.G.number_of_nodes() < 2:
            return {}

        # Build weighted undirected graph (use value_paise as weight)
        UG = nx.Graph()
        for u, v, data in self.G.edges(data=True):
            weight = 1.0
            if "value_paise" in data and data["value_paise"] > 0:
                weight = min(10.0, data["value_paise"] / 1e9)  # normalize: 1B paise = 10unit
            elif "amount_paise" in data and data["amount_paise"] > 0:
                weight = min(10.0, data["amount_paise"] / 1e9)
            UG.add_edge(u, v, weight=weight)

        try:
            pr = nx.pagerank(UG, alpha=alpha, weight="weight", max_iter=100)
            # Normalize to 0-10 range
            max_pr = max(pr.values()) if pr else 1
            normalized = {node: round(val / max_pr * 10, 3) for node, val in pr.items()}
            return normalized
        except Exception as e:
            logger.warning(f"PageRank failed: {e}")
            return {}

    def compute_network_risk_score(self) -> dict:
        """
        Compute risk scores for the subject company.
        Returns feature values to add to ML vector.
        """
        subject = None
        for node, attr in self.G.nodes(data=True):
            if attr.get("is_subject"):
                subject = node
                break

        features = {
            "network_risk_score": 0.0,
            "supplier_default_risk": 0.0,
            "promoter_network_risk": 0.0,
            "group_company_default_risk": 0.0,
        }

        if not subject or self.G.number_of_nodes() < 2:
            return features

        pr_scores = self.compute_pagerank_risk()

        # Network Risk: subject's own PageRank
        features["network_risk_score"] = round(pr_scores.get(subject, 0.0), 3)

        # Supplier Default Risk: avg PageRank of suppliers
        supplier_risks = []
        for src, tgt, data in self.G.edges(data=True):
            if tgt == subject and data.get("edge_type") == "BUYS_FROM":
                supplier_risks.append(pr_scores.get(src, 0.0))
        if supplier_risks:
            features["supplier_default_risk"] = round(np.mean(supplier_risks), 3)

        # Promoter Network Risk: avg PageRank of directors
        promoter_risks = []
        for src, tgt, data in self.G.edges(data=True):
            if tgt == subject and data.get("edge_type") == "DIRECTOR_OF":
                promoter_risks.append(pr_scores.get(src, 0.0))
        if promoter_risks:
            features["promoter_network_risk"] = round(np.mean(promoter_risks), 3)

        # Group Company Risk: avg PageRank of owned entities + lenders
        group_risks = []
        for src, tgt, data in self.G.edges(data=True):
            if src == subject and data.get("edge_type") == "OWNS":
                group_risks.append(pr_scores.get(tgt, 0.0))
            if tgt == subject and data.get("edge_type") == "BORROWS_FROM":
                group_risks.append(pr_scores.get(src, 0.0))
        if group_risks:
            features["group_company_default_risk"] = round(np.mean(group_risks), 3)

        logger.info(f"Graph intelligence features: {features}")
        return features

    def detect_director_cross_links(self) -> list:
        """
        Find directors who are linked to multiple companies in the graph.
        Cross-linked directors indicate promoter group risk.
        """
        director_companies = {}
        for node, attr in self.G.nodes(data=True):
            if attr.get("node_type") == "director":
                companies = [tgt for _, tgt, data in self.G.out_edges(node, data=True)
                             if data.get("edge_type") == "DIRECTOR_OF"]
                if len(companies) > 1:
                    director_companies[attr.get("name", node)] = companies

        return [
            {"director": name, "companies": cos, "cross_link_risk": len(cos) * 1.5}
            for name, cos in director_companies.items()
        ]
