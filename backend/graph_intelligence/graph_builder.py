"""
graph_builder.py
Build the corporate relationship graph from GST, MCA, and bank data.
"""
import networkx as nx
from loguru import logger


class CorporateGraphBuilder:
    """
    Builds a directed multigraph of:
      Nodes: companies, directors, banks
      Edges: DIRECTOR_OF, SUPPLIES_TO, BUYS_FROM, BORROWS_FROM, OWNS
    """

    def __init__(self):
        self.G = nx.DiGraph()

    def add_subject_company(self, gstin: str, company_name: str, cin: str = ""):
        self.G.add_node(gstin, node_type="subject", name=company_name, cin=cin, is_subject=True)

    def add_gst_data(self, gstr1: dict = None, gstr2a: dict = None):
        """Add buyer/supplier relationships from GST data."""
        subject_gstin = None
        for node, attr in self.G.nodes(data=True):
            if attr.get("is_subject"):
                subject_gstin = node
                break

        if not subject_gstin:
            return

        if gstr1:
            for buyer in gstr1.get("buyer_list", []):
                gstin = buyer.get("gstin", "")
                val = buyer.get("value", 0)
                if gstin:
                    if not self.G.has_node(gstin):
                        self.G.add_node(gstin, node_type="buyer", is_subject=False)
                    self.G.add_edge(subject_gstin, gstin, edge_type="SUPPLIES_TO", value_paise=val)

        if gstr2a:
            for supplier in gstr2a.get("supplier_list", []):
                gstin = supplier.get("gstin", "")
                val = supplier.get("value", 0)
                if gstin:
                    if not self.G.has_node(gstin):
                        self.G.add_node(gstin, node_type="supplier", is_subject=False)
                    self.G.add_edge(gstin, subject_gstin, edge_type="BUYS_FROM", value_paise=val)

    def add_directors(self, directors: list, subject_gstin: str):
        """Add director nodes and DIRECTOR_OF edges."""
        for d in directors:
            din = d.get("din", "")
            name = d.get("name", "")
            if din:
                node_id = f"DIN_{din}"
                self.G.add_node(node_id, node_type="director", name=name, din=din)
                self.G.add_edge(node_id, subject_gstin, edge_type="DIRECTOR_OF")

    def add_mca_charges(self, charges: list, subject_gstin: str):
        """Add lender nodes from charge registry."""
        for charge in charges:
            holder = charge.get("holder", "")
            if holder:
                lender_id = f"LENDER_{holder[:20].replace(' ', '_')}"
                self.G.add_node(lender_id, node_type="lender", name=holder)
                self.G.add_edge(lender_id, subject_gstin, edge_type="BORROWS_FROM",
                                amount_paise=charge.get("amount_paise", 0),
                                status=charge.get("status", ""))

    def add_related_parties(self, related_parties: list, subject_gstin: str):
        for rp in related_parties:
            rp_id = rp.get("cin", rp.get("name", ""))
            if rp_id:
                self.G.add_node(rp_id, node_type="related_party", name=rp.get("name", rp_id))
                self.G.add_edge(subject_gstin, rp_id, edge_type="OWNS",
                                relationship=rp.get("relationship", ""))

    def get_graph(self) -> nx.DiGraph:
        return self.G

    def summary(self) -> dict:
        return {
            "node_count": self.G.number_of_nodes(),
            "edge_count": self.G.number_of_edges(),
            "node_types": dict(nx.get_node_attributes(self.G, "node_type")),
        }
