import logging
from collections import defaultdict
import networkx as nx
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Listing, FssaiMatch, GraphEdge, Component

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def build_network_graph():
    """
    Builds the kitchen compliance network graph using NetworkX.
    Identifies connected components representing license-sharing clusters,
    and materializes edges and components to the database.
    
    Idempotent: clears components and graph_edges tables before running.
    """
    init_db()
    db: Session = SessionLocal()
    
    try:
        logger.info("Clearing existing network graph tables (idempotent run)...")
        db.query(Component).delete()
        db.query(GraphEdge).delete()
        db.commit()
        
        logger.info("Loading listings and FSSAI matches from database...")
        listings = db.query(Listing).all()
        matches = db.query(FssaiMatch).filter(
            (FssaiMatch.license_no.isnot(None)) & 
            (FssaiMatch.confidence >= settings.MATCH_THRESHOLD)
        ).all()
        
        # Maps for rapid lookup
        listing_map = {l.id: l for l in listings}
        match_map = {m.listing_id: m for m in matches}
        
        # Initialize NetworkX undirected graph
        G = nx.Graph()
        
        # Add all listings as nodes with attributes
        for listing in listings:
            # Check compliance status: active, expired, or unlicensed
            comp_status = "unlicensed"
            match = match_map.get(listing.id)
            if match:
                comp_status = "compliant" if match.status == "active" else "expired"
                
            G.add_node(
                listing.id,
                brand=listing.brand_name,
                city=listing.city,
                zone=listing.zone,
                compliance=comp_status
            )
            
        # Group listings by address to construct shared_address edges
        address_groups = defaultdict(list)
        for listing in listings:
            if listing.address and listing.address.strip():
                # Normalize address to lower case and strip white spaces for robust matching
                normalized_addr = listing.address.strip().lower()
                address_groups[normalized_addr].append(listing.id)
                
        # Group listings by FSSAI license number to construct shared_license edges
        license_groups = defaultdict(list)
        for match in matches:
            if match.license_no and match.license_no.strip():
                license_groups[match.license_no.strip()].append(match.listing_id)
                
        # List of edges to write to DB
        edges_to_save = []
        # Keep track of unique undirected pairs to avoid duplicate edge entries in DB
        seen_edges = set()
        
        # Add shared address edges
        logger.info("Adding shared address edges...")
        for addr, ids in address_groups.items():
            if len(ids) > 1:
                # Add edges between all pairs in the same address
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        u, v = ids[i], ids[j]
                        # Set edge in NetworkX graph
                        G.add_edge(u, v, edge_type="shared_address")
                        
                        edge_key = tuple(sorted((u, v)))
                        if (edge_key, "shared_address") not in seen_edges:
                            seen_edges.add((edge_key, "shared_address"))
                            edges_to_save.append(
                                GraphEdge(node_a=u, node_b=v, edge_type="shared_address", weight=1.0)
                            )
                            
        # Add shared license edges
        logger.info("Adding shared license edges...")
        for license_no, ids in license_groups.items():
            if len(ids) > 1:
                # Add edges between all pairs sharing the license
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        u, v = ids[i], ids[j]
                        G.add_edge(u, v, edge_type="shared_license")
                        
                        edge_key = tuple(sorted((u, v)))
                        if (edge_key, "shared_license") not in seen_edges:
                            seen_edges.add((edge_key, "shared_license"))
                            edges_to_save.append(
                                GraphEdge(node_a=u, node_b=v, edge_type="shared_license", weight=1.0)
                            )
                            
        # Write edges in bulk to the database
        logger.info(f"Saving {len(edges_to_save)} edges to graph_edges table...")
        db.bulk_save_objects(edges_to_save)
        db.commit()
        
        # Run connected components analysis
        logger.info("Computing connected components...")
        components = list(nx.connected_components(G))
        logger.info(f"Identified {len(components)} connected components.")
        
        # Prepare component records to materialize in DB
        components_to_save = []
        for comp_idx, comp_nodes in enumerate(components):
            comp_size = len(comp_nodes)
            for node_id in comp_nodes:
                components_to_save.append(
                    Component(listing_id=node_id, component_id=comp_idx, component_size=comp_size)
                )
                
        # Write component assignments in bulk to the database
        logger.info(f"Saving {len(components_to_save)} component mapping rows to components table...")
        db.bulk_save_objects(components_to_save)
        db.commit()
        
        # Print basic network metrics
        logger.info("Network metrics computed successfully:")
        logger.info(f" - Total Nodes: {G.number_of_nodes()}")
        logger.info(f" - Total Edges: {G.number_of_edges()}")
        large_clusters = sum(1 for c in components if len(c) > 1)
        max_cluster_size = max(len(c) for c in components) if components else 0
        logger.info(f" - Clusters of size > 1: {large_clusters}")
        logger.info(f" - Max Cluster Size: {max_cluster_size}")
        
    except Exception as e:
        logger.error(f"Error building compliance network graph: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    build_network_graph()
