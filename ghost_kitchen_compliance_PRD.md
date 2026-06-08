# Ghost Kitchen Compliance Map — PRD

## 1. Project Identity

**Project Name:** Ghost Kitchen Compliance Map
**Course:** Bio Safety Standards and Ethics (BT232AT)
**Institution:** RV College of Engineering, Bengaluru
**Team Size:** 4
**Timeline:** Half-semester (~6–7 weeks)
**License:** MIT

---

## 2. Problem Statement

India's food delivery sector serves over 80 million orders per month through Swiggy and Zomato. A significant and growing fraction of these orders are fulfilled by ghost kitchens — delivery-only food businesses with no physical storefront. Every such business is legally required to hold a valid FSSAI license under the Food Safety and Standards Act, 2006.

**The gap:** FSSAI's FoSCoS database is public. Swiggy and Zomato's listings are public. No tool, dataset, or research paper has ever connected these two sources at scale to answer a simple question: are the kitchens fulfilling your orders actually licensed?

Enforcement is reactive and under-resourced. Food safety officers operate with 40–60% vacancy rates across most states. Ghost kitchens have no physical sign, no walk-in presence, and no inspection trigger. They are the fastest-growing and least-visible segment in Indian food delivery.

This project builds the infrastructure that makes this compliance gap visible — for the first time, as a city-level dataset — and adds a network analysis layer that reveals the structural pattern of multi-brand license sharing that single-record database queries cannot expose.

---

## 3. Goals and Non-Goals

**Goals**
- Enumerate ghost kitchen brand listings across 10 Indian cities from Swiggy and Zomato
- Cross-reference each brand against FSSAI's FoSCoS license registry via fuzzy entity resolution
- Classify each listing into one of three anomaly types: unlicensed, expired license, or multi-brand single license
- Build a compliance graph where connected component analysis reveals license-sharing clusters
- Produce a city-zone choropleth map showing compliance rates with drill-down anomaly table
- Publish the dataset and codebase as open-source

**Non-Goals**
- Real-time monitoring or continuous scraping at production scale
- Building a consumer-facing product or mobile app
- Sending enforcement notices or identifying individual operators publicly by name
- Covering all cities in India (10 cities is the scoped target)
- Replacing FSSAI's enforcement infrastructure

---

## 4. Key Concepts and Definitions

**Ghost Kitchen / Cloud Kitchen:** A delivery-only food business with no dine-in presence. One physical address can host multiple virtual brands simultaneously.

**Virtual Brand:** A restaurant identity that exists only on a delivery platform — no signage, no walk-in. One FBO can operate 5–10 virtual brands from a single licensed kitchen.

**FBO (Food Business Operator):** The legal entity registered with FSSAI. The mismatch between a platform's marketing brand name and the FBO's registered legal name is the core entity resolution challenge.

**FoSCoS:** Food Safety Compliance System. FSSAI's official public portal at foscos.fssai.gov.in. Contains all food business operator registrations and licenses. Queryable by business name and state. The ground truth for compliance status.

**Compliance Rate:** (Brands with active FSSAI license confirmed via FoSCoS) ÷ (Total brands enumerated) × 100, computed per city zone.

**Three Anomaly Types:**
- **Type A — No Record:** Zero matching FoSCoS entry. Completely unlicensed.
- **Type B — Expired License:** License existed but has lapsed; brand still actively listed on platform.
- **Type C — Multi-Brand Single License:** Multiple distinct virtual brand names at the same address resolving to one FSSAI license number. Legally grey — FSSAI has no explicit multi-brand provision.

**Connected Component (Graph Theory):** A cluster of nodes where every node can reach every other via edges. In the compliance graph, each component is a cluster of brands tied together by shared address or shared license number.

---

## 5. System Architecture

Three layers, each with a distinct responsibility:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: SCRAPER                                           │
│  Playwright (headless Chromium, async)                      │
│  Targets: Swiggy listing pages + Zomato listing pages       │
│  Output: listings table in SQLite                           │
│  Schedule: one-time run per city (cron-extendable)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: MATCHER + GRAPH ENGINE                            │
│  FoSCoS API query per brand → RapidFuzz Jaro-Winkler        │
│  Confidence scoring → fssai_matches table                   │
│  NetworkX graph build → connected component analysis        │
│  Output: anomalies table + graph_edges table                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: DASHBOARD                                         │
│  FastAPI backend serving aggregated stats + graph data      │
│  React + Leaflet.js choropleth (compliance rate by zone)    │
│  D3 force-directed graph (compliance network)               │
│  Recharts bar/pie charts (anomaly breakdown)                │
│  Anomaly table with filters and drill-down                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Database Schema

```sql
-- Raw scraped listings
CREATE TABLE listings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,          -- 'swiggy' | 'zomato'
    brand_name      TEXT NOT NULL,
    url_slug        TEXT,
    city            TEXT NOT NULL,
    zone            TEXT,
    address         TEXT,
    latitude        REAL,
    longitude       REAL,
    price_range     TEXT,
    cuisine_tags    TEXT,                   -- JSON array
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FoSCoS match results
CREATE TABLE fssai_matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER REFERENCES listings(id),
    fssai_name      TEXT,                   -- matched FBO name from FoSCoS
    license_no      TEXT,
    license_type    TEXT,                   -- 'registration' | 'state' | 'central'
    status          TEXT,                   -- 'active' | 'expired' | 'suspended' | 'not_found'
    expiry_date     DATE,
    confidence      REAL,                   -- Jaro-Winkler score 0.0–1.0
    match_type      TEXT,                   -- 'exact' | 'fuzzy' | 'no_match'
    queried_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classified anomalies
CREATE TABLE anomalies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER REFERENCES listings(id),
    anomaly_type    TEXT NOT NULL,          -- 'A_no_record' | 'B_expired' | 'C_multi_brand'
    severity        TEXT,                   -- 'high' | 'medium' | 'low'
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Graph edges for network analysis
CREATE TABLE graph_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    node_a          INTEGER REFERENCES listings(id),
    node_b          INTEGER REFERENCES listings(id),
    edge_type       TEXT NOT NULL,          -- 'shared_address' | 'shared_license'
    weight          REAL DEFAULT 1.0
);

-- Connected components (materialized after NetworkX run)
CREATE TABLE components (
    listing_id      INTEGER REFERENCES listings(id),
    component_id    INTEGER NOT NULL,
    component_size  INTEGER NOT NULL
);
```

---

## 7. Scraper Specification

**Target pages:** City-level restaurant listing pages (e.g. `swiggy.com/city/bangalore/restaurants`)

**Fields extracted per listing:**
- Brand name (display name as shown on platform)
- URL slug (unique identifier per listing — used for deduplication)
- City and zone/area tag
- Listed address
- Latitude and longitude (from map embed or network request intercept)
- Price range (₹ / ₹₹ / ₹₹₹)
- Cuisine tags

**Anti-detection measures:**
- Randomized request delays (2–5 seconds between page loads)
- Rotating user-agent strings (standard Chrome browser fingerprint)
- Polite crawl rate — no parallel requests to same domain
- Respect robots.txt for all disallowed paths

**Deduplication:** URL slug is the primary deduplication key. Same brand appearing on both Swiggy and Zomato is stored as two records linked by a `canonical_brand_id` after fuzzy cross-platform name matching.

**Cities in scope (10):** Bengaluru, Mumbai, Delhi, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad, Jaipur, Lucknow

---

## 8. Entity Resolution (Matching) Specification

**Step 1 — FoSCoS Query**
Query FoSCoS FBO search by brand name + state. Returns a list of candidate registrations.

**Step 2 — Jaro-Winkler Scoring**
Score each candidate against the scraped brand name using RapidFuzz:
- Score ≥ 0.85 → **Confirmed match** (auto-accepted)
- Score 0.60–0.84 → **Ambiguous** (flagged for manual review queue)
- Score < 0.60 → **No match** (Type A anomaly candidate)

**Step 3 — Status Classification**
For confirmed matches:
- License status = active AND expiry date > today → **Compliant**
- License status = expired OR expiry date ≤ today → **Type B anomaly**
- License number shared with other listings at same address → **Type C anomaly**

**Confidence note:** All match confidence scores are stored and published alongside results. The system makes no hard verdicts — it produces evidence for human review.

---

## 9. Graph Analysis Specification

This is the technically distinguishing layer of the project. It transforms a flat lookup table into a network analysis problem.

**Graph construction (NetworkX):**

```python
G = nx.Graph()

# Add all enumerated brands as nodes
for listing in listings:
    G.add_node(listing.id,
               brand=listing.brand_name,
               city=listing.city,
               zone=listing.zone,
               compliance=listing.compliance_status)

# Add edges: shared address
for pair in same_address_pairs:
    G.add_edge(pair.a, pair.b,
               edge_type='shared_address')

# Add edges: shared license number
for pair in same_license_pairs:
    G.add_edge(pair.a, pair.b,
               edge_type='shared_license')
```

**Connected component analysis:**

```python
components = list(nx.connected_components(G))
# Each component = a cluster of brands tied by address or license
# Component size > 3 with shared_license edge = strong Type C anomaly signal
```

**What the graph reveals that the table cannot:**
- A component of size 8 sharing one license number = 7 brands operating outside their licensed scope
- A component mixing compliant and non-compliant nodes = a licensed operator running unlicensed virtual brands from the same address
- High-degree nodes = addresses functioning as de facto ghost kitchen hubs for multiple operators

**Graph metrics computed:**
- Component size distribution
- Degree distribution (brands by number of shared-address/license neighbors)
- Compliance rate within large components vs isolated nodes
- Top 10 highest-degree addresses (ghost kitchen hub candidates)

---

## 10. Dashboard Specification

This is where the project earns its visual credibility. The dashboard has four views.

### View 1 — City Compliance Map (Landing)

**Component:** Leaflet.js choropleth over India

**What it shows:**
- City zones colored by compliance rate
  - Dark green: >85% compliant
  - Yellow: 60–85%
  - Orange: 40–60%
  - Red: <40%
- Tooltip on hover: zone name, compliance rate, total brands enumerated, anomaly count breakdown

**Interactions:**
- Click zone → opens Zone Detail Panel (right sidebar)
- City selector dropdown → re-centers map
- Platform toggle (All / Swiggy only / Zomato only)
- Anomaly type filter (show zones with Type A / B / C anomalies)

**Zone Detail Panel:**
- Compliance rate with trend indicator
- Anomaly count by type (mini bar chart)
- Top 5 flagged brands in zone (name + anomaly type)
- Link to full anomaly table filtered by zone

---

### View 2 — Compliance Network Graph

**Component:** D3.js force-directed graph

**What it shows:**
- Every enumerated brand as a node
  - Node color: green = compliant, red = non-compliant, grey = ambiguous
  - Node size: proportional to number of virtual brands at same address
- Edges: blue = shared address, orange = shared license number
- Connected components are visually clustered by D3's force layout

**Interactions:**
- Click node → shows brand name, platform, city, compliance status, anomaly type
- Click component → highlights entire cluster, shows component stats in sidebar
- Filter by: city, anomaly type, edge type, minimum component size
- Slider: minimum component size (e.g. "show only clusters of 3+")
- Search: type brand name → highlights node and its component

**Sidebar on component selection:**
- Component ID and size
- Number of unique license numbers vs number of brands (ratio tells the story)
- List of all brands in cluster with individual compliance status
- Address shared by cluster (if applicable)

**Why this view matters for the presentation:**
This is the view that answers "so what?" A table of 5,000 brands means nothing. A graph where you can visually point to a cluster of 12 brands sharing one license, 9 of which are non-compliant, makes the compliance structure visceral and undeniable.

---

### View 3 — Anomaly Table

**Component:** AG Grid (sortable, filterable, paginated)

**Columns:**

| Column | Description |
|---|---|
| Brand Name | As listed on platform |
| Platform | Swiggy / Zomato |
| City | City |
| Zone | Sub-city area |
| Anomaly Type | A / B / C with color badge |
| Severity | High / Medium / Low |
| FSSAI Match | Matched FBO name (if any) |
| Confidence | Match confidence score |
| License Status | Active / Expired / Not Found |
| Expiry Date | License expiry (if applicable) |
| Component Size | Size of graph cluster this brand belongs to |

**Filters:** City, Platform, Anomaly Type, Severity, Confidence range, Component size ≥ N

**Export:** Download filtered results as CSV

---

### View 4 — Analytics Dashboard

**Component:** Recharts (bar, pie, scatter, histogram)

**Charts:**

1. **Compliance Rate by City** (horizontal bar chart)
   - 10 cities ranked by compliance rate
   - Stacked bars: compliant / Type A / Type B / Type C

2. **Anomaly Type Distribution** (donut chart)
   - Overall split of A vs B vs C across full dataset

3. **Platform Comparison** (grouped bar)
   - Swiggy vs Zomato compliance rates per city
   - Key finding: do platforms differ in enforcement stringency?

4. **Component Size Distribution** (histogram)
   - X-axis: component size (number of brands in cluster)
   - Y-axis: count of components of that size
   - Shows whether license-sharing is rare or systemic

5. **Compliance Rate vs Price Range** (scatter plot)
   - X-axis: average price range (₹ count)
   - Y-axis: compliance rate
   - Hypothesis: budget kitchens may have lower compliance rates

6. **Confidence Score Distribution** (histogram)
   - Shows quality of the entity resolution — how many matches were high-confidence vs ambiguous

---

## 11. API Specification (FastAPI Backend)

```
GET  /api/cities                        → list of all cities with compliance summary
GET  /api/city/{city}/zones             → zone-level compliance rates with GeoJSON
GET  /api/anomalies                     → paginated anomaly list (filters via query params)
GET  /api/anomalies/export              → CSV export of filtered anomaly list
GET  /api/graph/edges                   → graph edge list (node_a, node_b, edge_type)
GET  /api/graph/components              → component list with size and compliance stats
GET  /api/graph/component/{id}          → all brands in a specific component
GET  /api/stats/overview                → aggregate counts for analytics dashboard
GET  /api/stats/platform-comparison     → Swiggy vs Zomato compliance rates per city
GET  /api/stats/price-compliance        → compliance rate by price range
```

All endpoints return JSON. No authentication required — the dashboard is public.

---

## 12. Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Scraper | Python + Playwright (async) | JavaScript-heavy SPAs require real browser rendering |
| Entity Resolution | Python + RapidFuzz | Jaro-Winkler optimized for short name strings |
| Graph Analysis | Python + NetworkX | Standard library for graph construction and connected components |
| Database | SQLite | Zero-config, single-file, fully reproducible by anyone who clones the repo |
| Backend | FastAPI | Async, auto-docs, minimal boilerplate |
| Frontend | React + Vite + Tailwind CSS | Standard modern stack |
| Map | Leaflet.js | Open-source, handles GeoJSON zone boundaries natively |
| Network Graph | D3.js (force-directed) | Full control over force layout for compliance graph |
| Charts | Recharts | React-native, composable, handles all chart types needed |
| Data Table | AG Grid (community) | Handles 5,000+ rows with virtualized rendering |
| Deployment | Docker Compose | Single `docker-compose up` reproduces the entire system |

---

## 13. Emphasis: Analysis and UI

Since the scraper-matcher pipeline is the straightforward part, the project's academic weight rests on two things.

### Analysis Depth

**What you must be able to explain and defend:**

**Why Jaro-Winkler over Levenshtein or cosine?**
Business names are short strings where prefix matching is highly diagnostic. "Wow Biryani" vs "Wow Foods" — the shared prefix is a strong signal. Jaro-Winkler gives extra weight to prefix agreement specifically. Levenshtein treats all character positions equally; cosine requires tokenization which loses positional information in short strings.

**Why connected components over clustering algorithms (k-means, DBSCAN)?**
The relationship being modeled is exact — two brands either share an address or they don't. There's no distance metric to cluster on. Graph connectivity is the exact right abstraction. k-means requires a feature space and a predetermined k. DBSCAN requires a density notion. Neither applies here.

**What does a component of size N with shared_license edges actually mean legally?**
FSSAI licenses are issued per premises per business. A single license cannot legally cover multiple distinct brand identities without amendment. A large component sharing one license number is direct evidence of a systematic compliance gap, not noise.

**How do you handle false positives in the matcher?**
Confidence score + manual review queue for the 0.60–0.84 range. All results published with confidence scores. No brand is labeled non-compliant without a confidence ≥ 0.85. This makes the system conservative — it more likely undercounts non-compliance than overcounts it.

**What is the compliance formula and why that threshold?**
Compliant = active license + confidence ≥ 0.85 + expiry date in future. All three conditions must hold simultaneously. The 0.85 threshold was chosen because Jaro-Winkler at that level reliably separates true matches from coincidental partial matches in business name corpora.

### UI Emphasis

The network graph view is the presentation centrepiece. When presenting to the invigilator, lead with the graph, not the map. The map shows a number. The graph shows a structure. Pointing to a cluster of 10 brands sharing one license, with 7 of them flagged red, is a moment of genuine visual revelation that no table or chart can match.

**Key UI decisions to explain if asked:**

**Why D3 force-directed and not a static node-link diagram?**
Force layout emergently clusters connected components — you didn't manually arrange the clusters, the physics simulation produced them from the adjacency structure. That emergence is a meaningful property: the visual clusters correspond exactly to real-world license-sharing clusters.

**Why Leaflet.js and not Google Maps?**
Open-source, no API key, full GeoJSON control, works fully offline. For a reproducible academic project, this is the correct choice. Google Maps introduces an external dependency and usage limits.

**Why AG Grid for the table?**
5,000+ rows need virtualized rendering. A plain HTML table or basic React table would freeze the browser at that scale. AG Grid renders only the visible rows, handles sort and filter client-side, and exports CSV natively.

---

## 14. Deliverables

| Deliverable | Description |
|---|---|
| Scraper module | `scraper/` — Playwright scripts per platform, city config, output to SQLite |
| Matcher module | `matcher/` — FoSCoS query + RapidFuzz scoring + anomaly classifier |
| Graph module | `graph/` — NetworkX build + connected components + edge table writer |
| Backend | `backend/` — FastAPI app with all API endpoints |
| Frontend | `frontend/` — React app with all 4 dashboard views |
| Dataset | `data/compliance_dataset.csv` — full published dataset |
| Docker setup | `docker-compose.yml` — one-command full stack deployment |
| Report | Methodology + findings + ethics + future work |
| Presentation | 12-slide deck |

---

## 15. Ethics and Data Use

- All scraped data is publicly visible to any user of the platforms — no login, no private data
- Data collection is rate-limited and non-disruptive to platform servers
- No individual operator is named in public outputs — only aggregate statistics and anonymized cluster IDs
- Match confidence scores are always published alongside results — no hard verdicts
- The tool is read-only and transparency-focused — it produces evidence, not enforcement
- FoSCoS data is accessed via the public FBO search interface, designed explicitly for public verification
- Academic non-commercial use — no monetization, no resale of data

---

## 16. Success Criteria

| Metric | Target |
|---|---|
| Brands enumerated | ≥ 5,000 across 10 cities |
| Cities covered | 10 |
| FoSCoS match rate (confirmed + ambiguous) | ≥ 70% of enumerated brands |
| High-confidence matches (≥ 0.85) | ≥ 50% of enumerated brands |
| Anomaly types surfaced | All 3 (A, B, C) with real examples |
| Largest component found | ≥ 5 brands (validates graph analysis is non-trivial) |
| Dashboard views functional | All 4 |
| Dataset published | Yes (CSV on GitHub) |
| Docker deployment working | `docker-compose up` produces live dashboard |

---

## 17. Future Work

- Weekly automated re-scraping to track compliance trends over time
- License expiry date forecasting to predict future compliance degradation
- Integration with FSSAI enforcement order PDFs (RTI basis) to correlate licensing with actual food safety incidents
- Extension to tier-2 cities and additional platforms (Magicpin, Dunzo)
- Consumer-facing browser extension that shows compliance status inline on Swiggy/Zomato listing pages
- Partnership with CUTS International or similar consumer advocacy body for public dissemination
