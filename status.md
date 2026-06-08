# Project Status - Ghost Kitchen Compliance Map

## Current Progress

| Phase | Status | Details |
|---|---|---|
| **Phase 1: Project Scaffold + Docker Setup** | Completed | Directory structure, requirements.txt, config.py, Dockerfiles, docker-compose.yml, and environment variables initialized. |
| **Phase 2: Database Schema** | Completed | SQLite schema configured via SQLAlchemy in `models.py` and connection logic in `database.py`. Tables verified and initialized in `data/compliance.db`. |
| **Phase 3: Scraper** | In Progress | Playwright scraper with snapshot fallback (`SCRAPER_MOCK=True` support) implemented in `scraper.py`. First run succeeded and saved 2,850 listings. |

## Current State & Action Items

### Phase 3: Scraper
- **Bug Fixed:** Found and resolved a naming conflict where Swiggy and Zomato generated the same listing slugs (preventing duplicates from saving). Updated `scraper.py` to format slugs with platform suffixes (e.g., `-swiggy` / `-zomato`).
- **Next Step:** To load all 5,000 unique records, the database (`data/compliance.db`) and old snapshots (`backend/app/scraper/snapshots/*.html`) must be cleared before re-running `$env:PYTHONPATH="backend"; .venv\Scripts\python backend/app/scraper.py`.

### Remaining Phases
- **Phase 4:** Matcher (FoSCoS + Jaro-Winkler)
- **Phase 5:** Graph engine (NetworkX) + Seeder
- **Phase 6:** FastAPI backend (CORS, 10 endpoints)
- **Phase 7:** Frontend React Dashboard (Leaflet, D3, AG Grid, Recharts)
