import sqlite3
import os
import datetime

def init_raw_db():
    db_path = 'data/compliance.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read schema.sql
    schema_path = 'schema.sql'
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql = f.read()
            cursor.executescript(sql)
            
    # Count swiggy listings currently in database
    cursor.execute("SELECT COUNT(*) FROM listings WHERE city='Bengaluru' AND platform='swiggy' AND url_slug LIKE 'swiggy_%';")
    bengaluru_count = cursor.fetchone()[0]
    
    cities = [
        "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai",
        "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"
    ]
    
    # Insert or update status records
    for city in cities:
        cursor.execute("SELECT COUNT(*) FROM city_scrape_status WHERE city = ?;", (city,))
        exists = cursor.fetchone()[0]
        if not exists:
            if city == "Bengaluru" and bengaluru_count > 0:
                now = datetime.datetime.utcnow().isoformat()
                cursor.execute(
                    "INSERT INTO city_scrape_status (city, last_scraped_at, listing_count, status) VALUES (?, ?, ?, ?);",
                    (city, now, bengaluru_count, "completed")
                )
            else:
                cursor.execute(
                    "INSERT INTO city_scrape_status (city, last_scraped_at, listing_count, status) VALUES (?, NULL, 0, NULL);",
                    (city,)
                )
        else:
            # If Bengaluru exists but status is null, update it
            if city == "Bengaluru" and bengaluru_count > 0:
                cursor.execute(
                    "UPDATE city_scrape_status SET listing_count = ?, status = 'completed' WHERE city = ? AND status IS NULL;",
                    (bengaluru_count, city)
                )
                
    conn.commit()
    conn.close()
    print("Database schema initialized successfully.")

if __name__ == "__main__":
    init_raw_db()
