# Compliance Map

A full-stack application for detecting and analyzing food safety license violations using web scraping, fuzzy matching, and network analysis.

**Status:** ✅ Production-Ready | **Docker:** ✅ Ready

---

## 🎯 Overview

Compliance Map detects regulatory violations in food service operations by:

1. **Scraping** restaurant listings from major platforms across multiple regions
2. **Cross-referencing** against regulatory license databases
3. **Detecting** violations through fuzzy matching algorithms
4. **Analyzing** license-sharing networks using graph theory
5. **Visualizing** patterns on an interactive dashboard

### Key Features
- 210+ listings analyzed with 43.81% compliance rate
- 95+ unlicensed operations detected
- 27+ license-sharing clusters identified
- Maximum cluster size: 8 entities per license

---

## ✨ Features

- **Web Scraper** - Automated data collection from food delivery platforms
- **Fuzzy Matching** - Jaro-Winkler algorithm for license database matching
- **Network Analysis** - Connected component detection for fraud rings
- **Interactive Dashboard** - Real-time compliance visualization
- **Auto-backup System** - CSV snapshots with startup fallback
- **Docker Ready** - Complete containerization
- **REST API** - 12+ endpoints for data access

---

## 🛠️ Tech Stack

### Backend
- Python 3.11 + FastAPI
- SQLite3 + SQLAlchemy
- Playwright (scraping)
- RapidFuzz (fuzzy matching)
- NetworkX (graph analysis)

### Frontend
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS
- Leaflet, D3.js, Recharts (visualization)

### DevOps
- Docker & Docker Compose

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/username/compliance-map.git
cd compliance-map
docker-compose up -d
```

**Access:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Local Setup

**Backend:**
```bash
python -m venv .venv
source .venv/bin/activate
cd backend && pip install -r requirements.txt
playwright install chromium
cd .. && PYTHONPATH=backend uvicorn backend.app.main:app --reload
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

---

## 📁 Project Structure

```
compliance-map/
├── backend/
│   ├── app/
│   │   ├── main.py              # API & endpoints
│   │   ├── models.py            # Database models
│   │   ├── scraper.py           # Web scraper
│   │   ├── matcher.py           # Fuzzy matching
│   │   └── graph_engine.py      # Network analysis
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # UI components
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── data/
│   ├── compliance.db
│   └── snapshots/
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 🔌 API Reference

### Base URL
```
http://localhost:8000
```

### Statistics
- `GET /api/stats/overview?city={city}` - Compliance metrics
- `GET /api/cities` - Multi-region summary
- `GET /api/city/{city}/zones` - Zone breakdown

### Violations
- `GET /api/anomalies?city={city}` - Paginated violations
- `GET /api/anomalies/export` - CSV export

### Network
- `GET /api/graph/edges?city={city}` - Network data
- `GET /api/graph/components` - Clusters

### Admin
- `GET /api/admin/scrape-status` - Scrape progress
- `POST /api/admin/trigger-scrape` - Start pipeline
- `GET /api/admin/snapshots` - Backups
- `POST /api/admin/load-snapshot` - Restore

**Full docs:** http://localhost:8000/docs

---

## 🗄️ Database Schema

| Table | Purpose |
|-------|---------|
| listings | Raw data |
| fssai_matches | License matches |
| anomalies | Violations |
| graph_edges | Network connections |
| components | Clusters |
| city_scrape_status | Pipeline status |

### Violation Types
- **Type A**: Missing license
- **Type B**: Expired license  
- **Type C**: Shared license (fraud indicator)

---

## 📊 Analytics

**Sample Dataset (210 records)**
| Metric | Value |
|--------|-------|
| Compliant | 92 (43.81%) |
| Type A Violations | 95 |
| Type B Violations | 15 |
| Type C Violations | 27 |
| Network Edges | 203 |
| Connected Components | 136 |
| Fraud Clusters | 31 |

---

## 🐳 Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f backend

# Rebuild
docker-compose build --no-cache

# Status
docker-compose ps
```

---

## 📋 Requirements

- Docker & Docker Compose, OR
- Python 3.11+ and Node.js 20+
- 2GB disk space

---

## 🔧 Configuration

### Environment Variables (`.env`)
```
DATABASE_URL=sqlite:///./data/compliance.db
API_PORT=8000
FRONTEND_PORT=5173
```

### Docker Ports
- Backend: `8000`
- Frontend: `5173`

---

## 🚀 Deployment

Database and snapshots persist in `./data/` directory. On startup, if the database is empty, the system automatically restores from available snapshots.

---

**Open Source | MIT Licensed (if applicable) | Community-Driven**
