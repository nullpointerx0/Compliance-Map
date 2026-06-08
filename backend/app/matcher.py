import datetime
import hashlib
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from rapidfuzz.distance import JaroWinkler

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Listing, FssaiMatch, Anomaly

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Map cities to states for FoSCoS querying simulation
CITY_TO_STATE = {
    "Bengaluru": "Karnataka",
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Hyderabad": "Telangana",
    "Chennai": "Tamil Nadu",
    "Pune": "Maharashtra",
    "Kolkata": "West Bengal",
    "Ahmedabad": "Gujarat",
    "Jaipur": "Rajasthan",
    "Lucknow": "Uttar Pradesh"
}

def get_deterministic_license_no(address: str) -> str:
    """
    Generates a stable, realistic 14-digit FSSAI license number
    by hashing the physical address. This ensures that listings
    sharing the same address will resolve to the same license number,
    perfectly simulating license sharing (Type C anomaly).
    """
    if not address:
        address = "Default Address"
    h = int(hashlib.md5(address.encode("utf-8")).hexdigest(), 16)
    # FSSAI license numbers start with 1 (State/Central license) or 2 (Registration)
    prefix = "1" if h % 2 == 0 else "2"
    suffix = f"{h % 10000000000000:013d}"
    return prefix + suffix


def query_mock_foscos_candidates(brand_name: str, address: str, city: str, price_range: str = "₹₹") -> list:
    """
    Simulates querying the public FoSCoS database for a given brand name and address.
    Returns candidate FBO names, license numbers, status, and expiry dates.
    """
    state = CITY_TO_STATE.get(city, "Karnataka")
    
    # Use deterministic seeding based on brand_name to keep simulations reproducible
    seed_val = sum(ord(c) for c in brand_name) + sum(ord(c) for c in city)
    # Simple LCG pseudo-random generation to avoid setting random.seed globally
    rand_val = (seed_val * 1103515245 + 12345) & 0x7fffffff
    
    # Determine anomaly class for this brand name
    # 15% chance of Type A (unlicensed / no record)
    # 15% chance of Type B (expired license)
    # 70% chance of active license (some of which may be Type C if they share address)
    scenario_pct = rand_val % 100
    
    # Set Type A threshold based on price range:
    # Budget (₹): 50%, Mid-range (₹₹): 20%, Premium (₹₹₹): 5%
    if price_range == "₹":
        type_a_threshold = 50
    elif price_range == "₹₹":
        type_a_threshold = 20
    else:
        type_a_threshold = 5

    if scenario_pct < type_a_threshold:
        # Type A: completely unlicensed / no record found in database
        return []
        
    license_no = get_deterministic_license_no(address)
    license_type = "state" if license_no.startswith("1") else "registration"
    
    # Generate FBO names with varying degrees of similarity
    candidates = []
    
    # Option 1: High similarity (e.g. "Brand Name Foods Pvt Ltd")
    # Option 2: Moderate similarity (e.g. "Brand Name Dhaba" or "Owner's Name")
    # Option 3: Completely different (ambiguous match candidate)
    
    if scenario_pct >= 15 and scenario_pct < 30:
        # Type B Scenario (Expired license)
        fbo_name = f"{brand_name} Hospitality Services"
        expiry_date = datetime.date(2025, 5, 15)  # in the past
        status = "expired"
        candidates.append({
            "fssai_name": fbo_name,
            "license_no": license_no,
            "license_type": license_type,
            "status": status,
            "expiry_date": expiry_date
        })
    else:
        # Active license scenario
        # 10% chance of an ambiguous name (e.g., "Poonam Foods" for "Wow Biryani")
        # that will score in the 0.60-0.84 range
        if scenario_pct > 90:
            fbo_name = f"Sri Rama & Co. Food Services"
        else:
            # High similarity
            fbo_name = f"{brand_name} Foods"
            
        expiry_date = datetime.date(2027, 12, 31)  # in the future
        status = "active"
        candidates.append({
            "fssai_name": fbo_name,
            "license_no": license_no,
            "license_type": license_type,
            "status": status,
            "expiry_date": expiry_date
        })
        
    return candidates


def match_and_classify_listing(db: Session, listing: Listing) -> FssaiMatch:
    """
    Performs entity resolution for a single listing using Jaro-Winkler distance,
    saves the match, and returns it.
    """
    candidates = query_mock_foscos_candidates(listing.brand_name, listing.address, listing.city, listing.price_range)
    
    if not candidates:
        # No matches found in FoSCoS (Type A candidate)
        match_record = FssaiMatch(
            listing_id=listing.id,
            fssai_name=None,
            license_no=None,
            license_type=None,
            status="not_found",
            expiry_date=None,
            confidence=0.0,
            match_type="no_match"
        )
        db.add(match_record)
        return match_record
        
    best_candidate = None
    best_score = -1.0
    
    for candidate in candidates:
        # Calculate Jaro-Winkler similarity score
        score = JaroWinkler.similarity(listing.brand_name, candidate["fssai_name"])
        if score > best_score:
            best_score = score
            best_candidate = candidate
            
    # Classify match type based on Jaro-Winkler score
    if best_score >= settings.MATCH_THRESHOLD:
        match_type = "exact" if best_score >= 0.98 else "fuzzy"
    elif best_score >= settings.AMBIGUOUS_THRESHOLD:
        match_type = "fuzzy"  # ambiguous, flagged for review
    else:
        match_type = "no_match"
        
    match_record = FssaiMatch(
        listing_id=listing.id,
        fssai_name=best_candidate["fssai_name"],
        license_no=best_candidate["license_no"],
        license_type=best_candidate["license_type"],
        status=best_candidate["status"],
        expiry_date=best_candidate["expiry_date"],
        confidence=best_score,
        match_type=match_type
    )
    db.add(match_record)
    return match_record


def classify_anomalies(db: Session):
    """
    Processes all matches and classifies them into the 3 anomaly types:
    - Type A: No Record (confidence < 0.60 or status is not_found)
    - Type B: Expired License (confidence >= 0.85 and status is expired/expiry in past)
    - Type C: Multi-Brand Single License (multiple listings sharing the same license number)
    
    Idempotent: clears the anomalies table before run.
    """
    logger.info("Clearing existing classified anomalies...")
    db.query(Anomaly).delete()
    db.commit()
    
    # 1. Classify Type A anomalies: Completely unlicensed (no FSSAI record)
    # Listings with status = 'not_found' or Jaro-Winkler match confidence < 0.60
    type_a_query = db.query(Listing).join(FssaiMatch).filter(
        (FssaiMatch.status == "not_found") | (FssaiMatch.confidence < settings.AMBIGUOUS_THRESHOLD)
    )
    type_a_count = 0
    for listing in type_a_query:
        anomaly = Anomaly(
            listing_id=listing.id,
            anomaly_type="A_no_record",
            severity="high",
            notes=f"No matching FSSAI record found for brand '{listing.brand_name}' on FoSCoS database."
        )
        db.add(anomaly)
        type_a_count += 1
        
    # 2. Classify Type B anomalies: Expired or suspended license
    # Match confidence >= 0.85 but license status is expired or expiry date is past
    type_b_query = db.query(Listing).join(FssaiMatch).filter(
        (FssaiMatch.confidence >= settings.MATCH_THRESHOLD) & 
        ((FssaiMatch.status == "expired") | (FssaiMatch.expiry_date < datetime.date.today()))
    )
    type_b_count = 0
    for listing in type_b_query:
        match = listing.fssai_matches[0]
        anomaly = Anomaly(
            listing_id=listing.id,
            anomaly_type="B_expired",
            severity="high",
            notes=f"FSSAI license '{match.license_no}' (FBO: {match.fssai_name}) expired on {match.expiry_date}."
        )
        db.add(anomaly)
        type_b_count += 1
        
    # 3. Classify Type C anomalies: Multi-brand sharing a single license
    # Identify licenses shared by 3+ distinct brand names at the same address.
    from collections import defaultdict
    groups = defaultdict(list)
    
    confirmed_matches = db.query(Listing).join(FssaiMatch).filter(
        (FssaiMatch.license_no.isnot(None)) &
        (FssaiMatch.confidence >= settings.MATCH_THRESHOLD)
    ).all()
    
    for listing in confirmed_matches:
        addr = (listing.address or "").strip().lower()
        license_no = listing.fssai_matches[0].license_no
        key = (addr, license_no)
        groups[key].append(listing)
        
    type_c_count = 0
    for (addr, license_no), listings_in_group in groups.items():
        distinct_brands = set((l.brand_name or "").strip().lower() for l in listings_in_group)
        if len(distinct_brands) >= 3:
            cnt = len(listings_in_group)
            for listing in listings_in_group:
                anomaly = Anomaly(
                    listing_id=listing.id,
                    anomaly_type="C_multi_brand",
                    severity="medium",
                    notes=f"Shared FSSAI license '{license_no}' among {cnt} virtual brands at this location."
                )
                db.add(anomaly)
                type_c_count += 1
            
    db.commit()
    logger.info(f"Anomaly classification completed. Results:")
    logger.info(f" - Type A (No Record): {type_a_count}")
    logger.info(f" - Type B (Expired): {type_b_count}")
    logger.info(f" - Type C (License Sharing): {type_c_count}")


def run_matching():
    """
    Main execution pipeline for the entity resolution matcher.
    Queries unmatched records, applies Jaro-Winkler match logic, and
    performs anomaly classification.
    """
    init_db()
    db: Session = SessionLocal()
    
    # Resumable processing: Query listings that don't have an FSSAI match record yet
    unmatched_listings = db.query(Listing).outerjoin(FssaiMatch).filter(
        FssaiMatch.id.is_(None)
    ).all()
    
    total_unmatched = len(unmatched_listings)
    logger.info(f"Found {total_unmatched} unmatched listings to process.")
    
    processed = 0
    try:
        for listing in unmatched_listings:
            match_and_classify_listing(db, listing)
            processed += 1
            
            if processed % 500 == 0:
                db.commit()
                logger.info(f"Processed {processed}/{total_unmatched} listings...")
                
        db.commit()
        logger.info(f"Matching finished. Processed {processed} listings.")
        
        # Run anomaly classification pass after matching completes
        classify_anomalies(db)
        
    except Exception as e:
        logger.error(f"Error in matcher execution: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_matching()
