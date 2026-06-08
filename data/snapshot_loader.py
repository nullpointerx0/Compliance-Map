import os
import sys
import csv
import datetime
from sqlalchemy.orm import Session

# Add backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, init_db
from app.models import Listing

def export_snapshot(csv_path: str = "data/bengaluru_swiggy_snapshot.csv"):
    """
    Exports current Swiggy listings to a CSV snapshot.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        listings = db.query(Listing).filter(Listing.url_slug.like('swiggy_%')).all()
        # Ensure the directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'id', 'platform', 'brand_name', 'url_slug', 'city', 'zone',
                'address', 'latitude', 'longitude', 'price_range', 'cuisine_tags',
                'scraped_at'
            ])
            for l in listings:
                writer.writerow([
                    l.id,
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
        print(f"Successfully exported {len(listings)} real listings to {csv_path}")
    except Exception as e:
        print(f"Error exporting snapshot: {e}", file=sys.stderr)
    finally:
        db.close()

def load_snapshot(csv_path: str = "data/bengaluru_swiggy_snapshot.csv"):
    """
    Reads the CSV and inserts all rows, skipping existing url_slugs.
    """
    if not os.path.exists(csv_path):
        print(f"Snapshot file not found: {csv_path}", file=sys.stderr)
        return
        
    init_db()
    db: Session = SessionLocal()
    try:
        # Get existing url_slugs to skip duplicates
        existing_slugs = set(row[0] for row in db.query(Listing.url_slug).all() if row[0] is not None)
        
        inserted_count = 0
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
        print(f"Snapshot load summary: Inserted {inserted_count} new listings, skipped {skipped_count} existing.")
    except Exception as e:
        db.rollback()
        print(f"Error loading snapshot: {e}", file=sys.stderr)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        export_snapshot()
    else:
        load_snapshot()
