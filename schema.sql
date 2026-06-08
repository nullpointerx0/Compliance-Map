CREATE TABLE IF NOT EXISTS city_scrape_status (
    city TEXT PRIMARY KEY,
    last_scraped_at TIMESTAMP,
    listing_count INTEGER,
    status TEXT  -- 'completed' | 'in_progress' | 'failed'
);
