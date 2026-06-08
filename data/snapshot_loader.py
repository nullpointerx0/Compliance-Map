import os
import sys
import csv
import datetime
from sqlalchemy.orm import Session

# Add backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, init_db
from app.models import Listing

def export_snapshot(city: str = "Bengaluru", csv_path: str = None):
    """
    Exports current Swiggy listings for a specific city to a CSV snapshot.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        if csv_path is None:
            city_file = f"{city.lower().replace(' ', '_')}_snapshot.csv"
            csv_path = os.path.join("data", "snapshots", city_file)
            
        # Ensure target directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        listings = db.query(Listing).filter(
            Listing.city == city,
            Listing.url_slug.like('swiggy_%')
        ).all()
        
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'platform', 'brand_name', 'url_slug', 'city', 'zone',
                'address', 'latitude', 'longitude', 'price_range', 'cuisine_tags',
                'scraped_at'
            ])
            for l in listings:
                writer.writerow([
                    l.platform,
                    l.brand_name,
                    l.url_slug,
                    l.city,
                    l.zone,
                    l.address,
                    l.latitude,
                    l.longitude,
                    l.price_range,
                    l.cuisine_tags,
                    l.scraped_at.isoformat() if l.scraped_at else ""
                ])
        print(f"Successfully exported {len(listings)} real listings for {city} to {csv_path}")
    except Exception as e:
        print(f"Error exporting snapshot: {e}", file=sys.stderr)
    finally:
        db.close()

def load_snapshot(city: str = "Bengaluru", db: Session = None):
    """
    Reads the CSV from data/snapshots/{city}_snapshot.csv and inserts all rows, skipping existing url_slugs.
    Falls back to legacy path for Bengaluru if snapshot doesn't exist in data/snapshots/.
    """
    city_file = f"{city.lower().replace(' ', '_')}_snapshot.csv"
    csv_path = os.path.join("data", "snapshots", city_file)

    # Check fallback for legacy path
    if not os.path.exists(csv_path):
        if city.lower() == "bengaluru":
            legacy_path = "data/bengaluru_swiggy_snapshot.csv"
            if os.path.exists(legacy_path):
                csv_path = legacy_path
            else:
                print(f"Snapshot file not found: {csv_path}", file=sys.stderr)
                return 0
        else:
            print(f"Snapshot file not found: {csv_path}", file=sys.stderr)
            return 0

    is_local_db = False
    if db is None:
        init_db()
        db = SessionLocal()
        is_local_db = True

    inserted_count = 0
    try:
        # Get existing url_slugs to skip duplicates
        existing_slugs = set(row[0] for row in db.query(Listing.url_slug).all() if row[0] is not None)
        skipped_count = 0

        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url_slug = row['url_slug']
                if not url_slug:
                    continue
                if url_slug in existing_slugs:
                    skipped_count += 1
                    continue

                # Parse scraped_at
                scraped_at = None
                if row.get('scraped_at'):
                    try:
                        scraped_at = datetime.datetime.fromisoformat(row['scraped_at'])
                    except:
                        scraped_at = datetime.datetime.utcnow()
                else:
                    scraped_at = datetime.datetime.utcnow()

                lat = float(row['latitude']) if row.get('latitude') else None
                lng = float(row['longitude']) if row.get('longitude') else None

                listing = Listing(
                    platform=row['platform'],
                    brand_name=row['brand_name'],
                    url_slug=url_slug,
                    city=row['city'],
                    zone=row['zone'],
                    address=row['address'],
                    latitude=lat,
                    longitude=lng,
                    price_range=row['price_range'],
                    cuisine_tags=row['cuisine_tags'],
                    scraped_at=scraped_at
                )
                db.add(listing)
                existing_slugs.add(url_slug)
                inserted_count += 1

        db.commit()
        print(f"Snapshot load summary for {city}: Inserted {inserted_count} new listings, skipped {skipped_count} existing.")
    except Exception as e:
        db.rollback()
        print(f"Error loading snapshot for {city}: {e}", file=sys.stderr)
        inserted_count = 0
    finally:
        if is_local_db:
            db.close()

    return inserted_count

def load_snapshot_for_city(city: str, db: Session) -> int:
    """
    Loads snapshot for a given city using an existing database session.
    """
    return load_snapshot(city=city, db=db)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        city_arg = sys.argv[2] if len(sys.argv) > 2 else "Bengaluru"
        export_snapshot(city=city_arg)
    else:
        city_arg = sys.argv[1] if len(sys.argv) > 1 else "Bengaluru"
        load_snapshot(city=city_arg)
