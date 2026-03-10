"""
graph_features.py
Compute graph-derived ML features for a case.
Integrates with the ingestion orchestrator's feature vector.
"""
from loguru import logger


async def compute_graph_features(case_id: str, extraction: dict, mca_data: dict = None) -> dict:
    """
    Build corporate graph and extract ML features.
    """
    from graph_intelligence.graph_builder import CorporateGraphBuilder
    from graph_intelligence.risk_propagation_engine import RiskPropagationEngine

    builder = CorporateGraphBuilder()

    # Subject company
    subject_gstin = extraction.get("gstin", case_id)
    company_name = extraction.get("company_name", "")
    builder.add_subject_company(subject_gstin, company_name)

    # GST data
    gstr1 = extraction.get("gstr1")
    gstr2a = extraction.get("gstr2a")
    if gstr1 or gstr2a:
        builder.add_gst_data(gstr1, gstr2a)

    # Directors from MCA
    if mca_data:
        directors = mca_data.get("directors", [])
        builder.add_directors(directors, subject_gstin)
        charges = mca_data.get("charges", [])
        builder.add_mca_charges(charges, subject_gstin)

    # Related parties from annual report
    related = extraction.get("related_parties", [])
    if related:
        builder.add_related_parties(related, subject_gstin)

    G = builder.get_graph()
    summary = builder.summary()
    logger.info(f"Graph built: {summary['node_count']} nodes, {summary['edge_count']} edges")

    engine = RiskPropagationEngine(G)
    features = engine.compute_network_risk_score()
    cross_links = engine.detect_director_cross_links()

    features["director_cross_link_count"] = len(cross_links)
    features["graph_node_count"] = summary["node_count"]
    features["graph_edge_count"] = summary["edge_count"]

    return features
