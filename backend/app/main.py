import io
import math
import datetime
import pandas as pd
from typing import Optional, List
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db, init_db
from app.models import Listing, FssaiMatch, Anomaly, GraphEdge, Component, CityScrapeStatus


# Initialize database schema on startup
init_db()

app = FastAPI(
    title="Ghost Kitchen Compliance API",
    description="Backend service for tracking, matching, and analyzing licensing compliance among ghost kitchens in India.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Coordinates for generating zone box polygons for Leaflet maps
CITY_CENTERS = {
    "Bengaluru": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
}

CITY_ZONES = {
    "Bengaluru": ["Koramangala", "Indiranagar", "Jayanagar", "HSR Layout", "Whitefield", "Malleshwaram"],
    "Mumbai": ["Bandra", "Andheri", "Colaba", "Dadar", "Powai", "Thane"],
    "Delhi": ["Connaught Place", "Karol Bagh", "South Ext", "Dwarka", "Vasant Kunj", "Rohini"],
    "Hyderabad": ["Gachibowli", "Jubilee Hills", "Banjara Hills", "Madhapur", "Secunderabad", "Begumpet"],
    "Chennai": ["Adyar", "T-Nagar", "Mylapore", "Velachery", "Anna Nagar", "Nungambakkam"],
    "Pune": ["Kothrud", "Koregaon Park", "Aundh", "Baner", "Viman Nagar", "Hinjewadi"],
    "Kolkata": ["Salt Lake", "Park Street", "Ballygunge", "Gariahat", "Newtown", "Howrah"],
    "Ahmedabad": ["Satellite", "Vastrapur", "Navrangpura", "Bodakdev", "C G Road", "Gota"],
    "Jaipur": ["C-Scheme", "Malviya Nagar", "Vaishali Nagar", "Mansarovar", "Raja Park", "Bani Park"],
    "Lucknow": ["Hazratganj", "Gomti Nagar", "Aliganj", "Indira Nagar", "Aminabad", "Ashiyana"]
}

# --- 1. list of all cities with compliance summary ---
@app.get("/api/cities")
def get_cities_summary(db: Session = Depends(get_db)):
    """
    Returns a list of all 10 configured cities with an aggregated compliance summary,
    including total listings, compliant listings, and counts of Type A, B, and C anomalies.
    """
    summaries = []
    
    for city in settings.CITIES:
        total = db.query(Listing).filter(Listing.city == city).count()
        if total == 0:
            summaries.append({
                "city": city,
                "total_listings": 0,
                "compliant_count": 0,
                "compliance_rate": 100.0,
                "anomalies_breakdown": {"A": 0, "B": 0, "C": 0}
            })
            continue
            
        # Compliant condition: active license, confidence >= match threshold, and expiry in future
        compliant = db.query(Listing).join(FssaiMatch).filter(
            (Listing.city == city) &
            (FssaiMatch.status == "active") &
            (FssaiMatch.confidence >= settings.MATCH_THRESHOLD) &
            (FssaiMatch.expiry_date >= datetime.date.today())
        ).count()
        
        type_a = db.query(Listing).join(Anomaly).filter(
            (Listing.city == city) & (Anomaly.anomaly_type == "A_no_record")
        ).count()
        
        type_b = db.query(Listing).join(Anomaly).filter(
            (Listing.city == city) & (Anomaly.anomaly_type == "B_expired")
        ).count()
        
        type_c = db.query(Listing).join(Anomaly).filter(
            (Listing.city == city) & (Anomaly.anomaly_type == "C_multi_brand")
        ).count()
        
        compliance_rate = round((compliant / total) * 100, 2)
        
        summaries.append({
            "city": city,
            "total_listings": total,
            "compliant_count": compliant,
            "compliance_rate": compliance_rate,
            "anomalies_breakdown": {
                "A": type_a,
                "B": type_b,
                "C": type_c
            }
        })
        
    return summaries

# --- 2. zone-level compliance rates with GeoJSON ---
@app.get("/api/city/{city}/zones")
def get_city_zones_geojson(city: str, db: Session = Depends(get_db)):
    """
    Computes zone-level compliance rates for the specified city and generates
    a valid GeoJSON FeatureCollection representation containing bounding box polygon coordinates
    for each sub-city zone. Used directly for Leaflet choropleth rendering.
    """
    if city not in CITY_CENTERS:
        raise HTTPException(status_code=404, detail="City not found in configuration")
        
    center_lat, center_lng = CITY_CENTERS[city]
    zones_list = CITY_ZONES.get(city, [])
    
    # Fetch all listings in the city to aggregate compliance rates by zone
    listings = db.query(Listing).filter(func.lower(Listing.city) == city.lower()).all()
    
    # Store aggregated zone data
    zone_data = {}
    for zone in zones_list:
        zone_data[zone] = {
            "total_listings": 0,
            "compliant_count": 0,
            "type_a": 0,
            "type_b": 0,
            "type_c": 0
        }
        
    for listing in listings:
        z = listing.zone
        if z not in zone_data:
            zone_data[z] = {
                "total_listings": 0,
                "compliant_count": 0,
                "type_a": 0,
                "type_b": 0,
                "type_c": 0
            }
            
        zone_data[z]["total_listings"] += 1
        
        # Check if compliant
        is_compliant = False
        if listing.fssai_matches:
            match = listing.fssai_matches[0]
            if (match.status == "active" and 
                match.confidence >= settings.MATCH_THRESHOLD and 
                match.expiry_date >= datetime.date.today()):
                is_compliant = True
                
        if is_compliant:
            zone_data[z]["compliant_count"] += 1
            
        # Check anomalies
        for anomaly in listing.anomalies:
            if anomaly.anomaly_type == "A_no_record":
                zone_data[z]["type_a"] += 1
            elif anomaly.anomaly_type == "B_expired":
                zone_data[z]["type_b"] += 1
            elif anomaly.anomaly_type == "C_multi_brand":
                zone_data[z]["type_c"] += 1
                
    # Build GeoJSON Features
    features = []
    for idx, zone in enumerate(zones_list):
        z_stats = zone_data.get(zone, {
            "total_listings": 0, "compliant_count": 0, "type_a": 0, "type_b": 0, "type_c": 0
        })
        
        total = z_stats["total_listings"]
        rate = round((z_stats["compliant_count"] / total) * 100, 2) if total > 0 else 100.0
        
        # Place the zone box radially around the city center center point
        angle = (2 * math.pi * idx) / len(zones_list)
        dist = 0.022  # geographic coordinate radius
        
        zone_lat = center_lat + dist * math.sin(angle)
        zone_lng = center_lng + dist * math.cos(angle)
        
        # Define small bounding square box for this zone (Leaflet polygon)
        r = 0.007
        coords = [
            [zone_lng - r, zone_lat - r],
            [zone_lng + r, zone_lat - r],
            [zone_lng + r, zone_lat + r],
            [zone_lng - r, zone_lat + r],
            [zone_lng - r, zone_lat - r]
        ]
        
        feature = {
            "type": "Feature",
            "id": f"{city.lower()}-{zone.lower().replace(' ', '-')}",
            "properties": {
                "name": zone,
                "city": city,
                "compliance_rate": rate,
                "total_listings": total,
                "compliant_count": z_stats["compliant_count"],
                "anomaly_count": z_stats["type_a"] + z_stats["type_b"] + z_stats["type_c"],
                "anomalies": {
                    "A": z_stats["type_a"],
                    "B": z_stats["type_b"],
                    "C": z_stats["type_c"]
                }
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        features.append(feature)
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

# Helper to build dynamic database query filters for anomalies
def get_anomalies_filtered_query(
    db: Session,
    city: Optional[str] = None,
    platform: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    severity: Optional[str] = None,
    min_component_size: Optional[int] = None
):
    """
    Helper function to compose a database query on anomalies table applying search filters.
    """
    query = db.query(Anomaly).join(Listing).outerjoin(FssaiMatch).outerjoin(Component)
    
    if city:
        query = query.filter(Listing.city == city)
    if platform:
        query = query.filter(Listing.platform == platform)
    if anomaly_type:
        query = query.filter(Anomaly.anomaly_type == anomaly_type)
    if severity:
        query = query.filter(Anomaly.severity == severity)
    if min_component_size:
        query = query.filter(Component.component_size >= min_component_size)
        
    return query

# --- 3. paginated anomaly list (filters via query params) ---
@app.get("/api/anomalies")
def get_anomalies_paginated(
    city: Optional[str] = None,
    platform: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    severity: Optional[str] = None,
    min_component_size: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Fetches a paginated list of kitchen listings flagged with FSSAI/compliance anomalies.
    Supports filters for city, platform, anomaly type, severity, and minimum network component size.
    """
    query = get_anomalies_filtered_query(db, city, platform, anomaly_type, severity, min_component_size)
    total_records = query.count()
    
    # Fetch offset slice
    offset = (page - 1) * page_size
    records = query.order_by(Anomaly.id.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for rec in records:
        l = rec.listing
        m = l.fssai_matches[0] if l.fssai_matches else None
        c = l.component
        
        items.append({
            "id": rec.id,
            "listing_id": l.id,
            "brand_name": l.brand_name,
            "platform": l.platform,
            "city": l.city,
            "zone": l.zone,
            "address": l.address,
            "anomaly_type": rec.anomaly_type,
            "severity": rec.severity,
            "notes": rec.notes,
            "fssai_name": m.fssai_name if m else None,
            "license_no": m.license_no if m else None,
            "confidence": round(m.confidence, 3) if m else 0.0,
            "status": m.status if m else "not_found",
            "expiry_date": m.expiry_date.isoformat() if m and m.expiry_date else None,
            "component_size": c.component_size if c else 1,
            "component_id": c.component_id if c else None
        })
        
    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / page_size),
        "data": items
    }

# --- 4. CSV export of filtered anomaly list ---
@app.get("/api/anomalies/export")
def export_anomalies_csv(
    city: Optional[str] = None,
    platform: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    severity: Optional[str] = None,
    min_component_size: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Generates and downloads a CSV export file containing the complete list of filtered anomalies.
    """
    query = get_anomalies_filtered_query(db, city, platform, anomaly_type, severity, min_component_size)
    records = query.all()
    
    rows = []
    for rec in records:
        l = rec.listing
        m = l.fssai_matches[0] if l.fssai_matches else None
        c = l.component
        
        rows.append({
            "Brand Name": l.brand_name,
            "Platform": l.platform.capitalize(),
            "City": l.city,
            "Zone": l.zone,
            "Address": l.address,
            "Anomaly Type": rec.anomaly_type,
            "Severity": rec.severity.upper(),
            "Notes": rec.notes,
            "FSSAI Name Match": m.fssai_name if m else "",
            "License No": m.license_no if m else "",
            "Match Confidence": round(m.confidence, 3) if m else 0.0,
            "License Status": m.status if m else "Not Found",
            "Expiry Date": m.expiry_date.isoformat() if m and m.expiry_date else "",
            "Network Component Size": c.component_size if c else 1
        })
        
    df = pd.DataFrame(rows)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=compliance_anomalies.csv"
    return response

# --- 5. graph edge list ---
@app.get("/api/graph/edges")
def get_graph_edges(
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns lists of network graph nodes and edges for visualizing clusters.
    Supports filtering by city to reduce edge payload sizes for smooth D3 renders.
    """
    # 1. Fetch listings
    listings_query = db.query(Listing).outerjoin(FssaiMatch).outerjoin(Component)
    if city:
        listings_query = listings_query.filter(Listing.city == city)
        
    listings = listings_query.all()
    
    nodes = []
    node_ids = set()
    
    # Collect all listings as nodes
    for l in listings:
        match = l.fssai_matches[0] if l.fssai_matches else None
        comp_status = "unlicensed"
        if match:
            comp_status = "compliant" if match.status == "active" else "expired"
            
        nodes.append({
            "id": l.id,
            "brand_name": l.brand_name,
            "platform": l.platform,
            "city": l.city,
            "zone": l.zone,
            "address": l.address,
            "compliance_status": comp_status,
            "component_size": l.component.component_size if l.component else 1,
            "component_id": l.component.component_id if l.component else None
        })
        node_ids.add(l.id)
        
    # 2. Fetch edges
    edges_query = db.query(GraphEdge)
    edges = edges_query.all()
    
    edges_list = []
    for e in edges:
        # If filtering by city, only return edges connecting nodes inside that city
        if city:
            if e.node_a not in node_ids or e.node_b not in node_ids:
                continue
                
        edges_list.append({
            "source": e.node_a,
            "target": e.node_b,
            "edge_type": e.edge_type,
            "weight": e.weight
        })
        
    return {
        "nodes": nodes,
        "links": edges_list
    }

# --- 6. connected components list with size and compliance stats ---
@app.get("/api/graph/components")
def get_components_summary(
    city: Optional[str] = None,
    min_size: int = Query(2, ge=1),
    db: Session = Depends(get_db)
):
    """
    Returns a summarized list of connected components (networks of shared licenses/addresses).
    Each summary details size, compliance rate, member brands, and physical addresses.
    """
    # Fetch components
    query = db.query(Component.component_id, Component.component_size).distinct()
    if min_size:
        query = query.filter(Component.component_size >= min_size)
        
    all_comps = query.order_by(Component.component_size.desc()).all()
    
    summary = []
    for comp_id, comp_size in all_comps:
        # Get listings inside this component
        l_query = db.query(Listing).join(Component).filter(Component.component_id == comp_id)
        if city:
            l_query = l_query.filter(Listing.city == city)
            
        listings_in_comp = l_query.all()
        if not listings_in_comp:
            continue
            
        brands = [l.brand_name for l in listings_in_comp]
        addresses = list(set([l.address for l in listings_in_comp if l.address]))
        
        # Calculate compliance counts
        compliant_cnt = 0
        for l in listings_in_comp:
            if l.fssai_matches:
                m = l.fssai_matches[0]
                if (m.status == "active" and 
                    m.confidence >= settings.MATCH_THRESHOLD and 
                    m.expiry_date >= datetime.date.today()):
                    compliant_cnt += 1
                    
        compliance_rate = round((compliant_cnt / len(listings_in_comp)) * 100, 2)
        
        summary.append({
            "component_id": comp_id,
            "component_size": len(listings_in_comp),
            "original_size": comp_size,
            "compliant_count": compliant_cnt,
            "compliance_rate": compliance_rate,
            "brands": list(set(brands))[:8], # limit view strings
            "addresses": addresses[:3] # primary addresses
        })
        
    return summary

# --- 7. all brands in a specific component ---
@app.get("/api/graph/component/{id}")
def get_component_detail(id: int, db: Session = Depends(get_db)):
    """
    Returns full details for all kitchen listings belonging to the specified component ID.
    """
    listings = db.query(Listing).join(Component).filter(Component.component_id == id).all()
    if not listings:
        raise HTTPException(status_code=404, detail="Network component not found")
        
    details = []
    for l in listings:
        match = l.fssai_matches[0] if l.fssai_matches else None
        
        comp_status = "unlicensed"
        if match:
            comp_status = "compliant" if match.status == "active" else "expired"
            
        anomaly_type = l.anomalies[0].anomaly_type if l.anomalies else None
        details.append({
            "id": l.id,
            "brand_name": l.brand_name,
            "platform": l.platform,
            "city": l.city,
            "zone": l.zone,
            "address": l.address,
            "price_range": l.price_range,
            "cuisine_tags": l.cuisine_tags,
            "compliance_status": comp_status,
            "anomaly_type": anomaly_type,
            "license_no": match.license_no if match else None,
            "fssai_name": match.fssai_name if match else None,
            "confidence": round(match.confidence, 3) if match else 0.0
        })
        
    return details

# --- 8. aggregate counts for analytics dashboard ---
@app.get("/api/stats/overview")
def get_stats_overview(db: Session = Depends(get_db)):
    """
    Aggregates global counter metrics for dashboard headers, such as total listings,
    total compliant kitchens, and splits of Type A, B, and C anomalies.
    """
    total = db.query(Listing).count()
    
    compliant = db.query(Listing).join(FssaiMatch).filter(
        (FssaiMatch.status == "active") &
        (FssaiMatch.confidence >= settings.MATCH_THRESHOLD) &
        (FssaiMatch.expiry_date >= datetime.date.today())
    ).count()
    
    type_a = db.query(Anomaly).filter(Anomaly.anomaly_type == "A_no_record").count()
    type_b = db.query(Anomaly).filter(Anomaly.anomaly_type == "B_expired").count()
    type_c = db.query(Anomaly).filter(Anomaly.anomaly_type == "C_multi_brand").count()
    
    return {
        "total_listings": total,
        "compliant_count": compliant,
        "compliance_rate": round((compliant / total) * 100, 2) if total > 0 else 100.0,
        "anomalies": {
            "total": type_a + type_b + type_c,
            "type_a": type_a,
            "type_b": type_b,
            "type_c": type_c
        }
    }

# --- 9. Swiggy vs Zomato compliance rates per city ---
@app.get("/api/stats/platform-comparison")
def get_platform_comparison(db: Session = Depends(get_db)):
    """
    Compares FSSAI compliance rates between Swiggy and Zomato across all 10 cities,
    surfacing differences in platform-level enforcement.
    """
    data = []
    for city in settings.CITIES:
        city_stats = {"city": city}
        
        for platform in ["swiggy", "zomato"]:
            total = db.query(Listing).filter((Listing.city == city) & (Listing.platform == platform)).count()
            
            if total == 0:
                city_stats[f"{platform}_rate"] = 100.0
                city_stats[f"{platform}_count"] = 0
                continue
                
            compliant = db.query(Listing).join(FssaiMatch).filter(
                (Listing.city == city) &
                (Listing.platform == platform) &
                (FssaiMatch.status == "active") &
                (FssaiMatch.confidence >= settings.MATCH_THRESHOLD) &
                (FssaiMatch.expiry_date >= datetime.date.today())
            ).count()
            
            city_stats[f"{platform}_rate"] = round((compliant / total) * 100, 2)
            city_stats[f"{platform}_count"] = total
            
        data.append(city_stats)
        
    return data

# --- 10. compliance rate by price range ---
@app.get("/api/stats/price-compliance")
def get_price_compliance(db: Session = Depends(get_db)):
    """
    Aggregates licensing compliance rates grouped by listings' price ranges (₹ / ₹₹ / ₹₹₹),
    testing the academic hypothesis that budget kitchens exhibit lower compliance.
    """
    data = []
    price_brackets = ["₹", "₹₹", "₹₹₹"]
    
    for price in price_brackets:
        total = db.query(Listing).filter(Listing.price_range == price).count()
        if total == 0:
            data.append({"price_range": price, "total_listings": 0, "compliance_rate": 100.0})
            continue
            
        compliant = db.query(Listing).join(FssaiMatch).filter(
            (Listing.price_range == price) &
            (FssaiMatch.status == "active") &
            (FssaiMatch.confidence >= settings.MATCH_THRESHOLD) &
            (FssaiMatch.expiry_date >= datetime.date.today())
        ).count()
        
        data.append({
            "price_range": price,
            "total_listings": total,
            "compliance_rate": round((compliant / total) * 100, 2)
        })
        
    return data


# --- 11. Background Scraper & Pipeline Trigger ---
from app.database import SessionLocal
from app.scraper import scrape_city
from app.matcher import run_matching
from app.graph_engine import build_network_graph
import threading
from pydantic import BaseModel
from fastapi.responses import JSONResponse

class TriggerScrapeRequest(BaseModel):
    cities: Optional[List[str]] = None

pipeline_status = {
    "running": False,
    "step": "idle",
    "started_at": None,
    "finished_at": None,
    "error": None
}

def run_pipeline_task(cities: List[str]):
    global pipeline_status
    started_time = datetime.datetime.utcnow().isoformat()
    pipeline_status = {
        "running": True,
        "step": "scraping",
        "started_at": started_time,
        "finished_at": None,
        "error": None
    }
    
    db = SessionLocal()
    try:
        # Step 1: Scrape target cities sequentially
        for city in cities:
            scrape_city(db, city)
            
        # Step 2: Match
        pipeline_status["step"] = "matching"
        run_matching()
        
        # Step 3: Graph Engine
        pipeline_status["step"] = "graph_generation"
        build_network_graph()
        
        pipeline_status["running"] = False
        pipeline_status["step"] = "completed"
        pipeline_status["finished_at"] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        pipeline_status["running"] = False
        pipeline_status["step"] = "failed"
        pipeline_status["error"] = error_msg
        pipeline_status["finished_at"] = datetime.datetime.utcnow().isoformat()
    finally:
        db.close()

@app.post("/api/admin/trigger-scrape")
def trigger_scrape(req: Optional[TriggerScrapeRequest] = None, db: Session = Depends(get_db)):
    global pipeline_status
    if pipeline_status["running"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Pipeline is already running"}
        )
        
    cities_to_scrape = []
    if req and req.cities is not None:
        cities_to_scrape = req.cities
    else:
        # Default: scrape only cities with no existing data (completed status is not set)
        unscraped = db.query(CityScrapeStatus).filter(
            (CityScrapeStatus.status.is_(None)) | (CityScrapeStatus.status != 'completed')
        ).limit(2).all()
        cities_to_scrape = [c.city for c in unscraped]
        
    if not cities_to_scrape:
        return JSONResponse(
            status_code=400,
            content={"error": "No unscraped cities found to trigger"}
        )
        
    if len(cities_to_scrape) > 2:
        return JSONResponse(
            status_code=400,
            content={"error": "Max 2 cities per scrape run to avoid rate limiting"}
        )
        
    for city in cities_to_scrape:
        if city not in settings.CITIES:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid city specified: {city}"}
            )
            
    thread = threading.Thread(target=run_pipeline_task, args=(cities_to_scrape,))
    thread.daemon = True
    thread.start()
    
    cities_str = ", ".join(cities_to_scrape)
    return {
        "status": "pipeline_started",
        "message": f"Scraping {cities_str} data. Check /api/admin/pipeline-status for progress."
    }

@app.get("/api/admin/pipeline-status")
def get_pipeline_status():
    global pipeline_status
    return pipeline_status

@app.get("/api/admin/scrape-status")
def get_scrape_status(db: Session = Depends(get_db)):
    records = db.query(CityScrapeStatus).all()
    records_map = {r.city: r for r in records}
    
    results = []
    for city in settings.CITIES:
        record = records_map.get(city)
        if record:
            results.append({
                "city": city,
                "status": record.status,
                "last_scraped_at": record.last_scraped_at.isoformat() if record.last_scraped_at else None,
                "listing_count": record.listing_count or 0
            })
        else:
            results.append({
                "city": city,
                "status": None,
                "last_scraped_at": None,
                "listing_count": 0
            })
    return results


