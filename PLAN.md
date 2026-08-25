# Committee of Fifteen — Vercel + Railway Plan

**Repo:** https://github.com/tedrubin80/commitieoffifteen (public — no secrets in git)  
**Data:** Hugging Face + Kaggle (derived tables only; see [docs/DATA.md](docs/DATA.md))

**Goal:** Public portfolio app — interactive 1900 NYC vice-investigation map + searchable mined text — hosted on **Vercel** (Next.js + Postgres) with **Railway** (Python batch workers).

**Priority order:** 1) Map + geocoding → 2) Text mining → 3) Polish / launch

---

## What we already have (Hetzner box)

| Asset | Count | Notes |
|-------|------:|-------|
| MODS metadata | 1,731 | precinct hierarchy parsed |
| Page JPEGs | 1,731 | ~528 MB, NYPL CDN IDs kept |
| Address records | 1,710 | title = street address |
| Unique addresses | ~1,708 | geocode once, join many |
| Precincts | 36 | e.g. Precinct 15 → 233 records |
| Enriched table | ✓ | `data/processed/committee_of_fifteen_enriched.parquet` |
| OCR | in progress | Tesseract on ~340×760 scans; noisy but searchable |

**Rights:** UND — link to NYPL for images; do **not** bulk-rehost scans on Blob/CDN.

---

## Target architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Vercel                                                      │
│  ┌──────────────────┐    ┌─────────────────────────────┐   │
│  │ Next.js 15 app   │───▶│ Vercel Postgres (Neon)      │   │
│  │ /map /search     │    │ records · geocodes · ocr    │   │
│  │ /record/[uuid]   │    │ mining_terms · fts indexes  │   │
│  └────────┬─────────┘    └──────────────▲──────────────┘   │
│           │                              │                   │
│  Serverless API routes (read-heavy)      │ writes            │
└───────────┼──────────────────────────────┼───────────────────┘
            │                              │
            │  NEXT_PUBLIC_*               │  POSTGRES_URL
            ▼                              │
┌───────────────────────────────────────────┴─────────────────┐
│  Railway                                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Python worker service (always-on or cron)               │ │
│  │  · seed.py      — load parquet → Postgres (one-time)   │ │
│  │  · geocode.py   — NYC GeoClient / Mapbox batch         │ │
│  │  · ocr.py       — finish OCR, upsert text              │ │
│  │  · mine.py      — keywords, entities, aggregates        │ │
│  └────────────────────────────────────────────────────────┘ │
│  Optional: FastAPI `/health` + `/trigger/geocode` for manual  │
└───────────────────────────────────────────────────────────────┘

Local (Hetzner): crawl + initial OCR only — not deployed
```

**Why split this way**

- **Vercel:** global map UI, fast reads, Postgres already provisioned, preview deploys per PR
- **Railway:** long jobs (1,708 geocode calls, 1,731 OCR passes, mining) — no 10s/300s serverless limits
- Same pattern as `social-register-app` (web on Vercel, compute on Railway), but **Postgres on Vercel** instead of SQLite volume

**Vercel ↔ Railway integration:** connect via Vercel Marketplace Railway plugin or manually copy `POSTGRES_URL` (and `POSTGRES_URL_NON_POOLING` for migrations) into Railway service env. Railway worker writes; Vercel app reads.

---

## Repo layout (monorepo)

```
committee-of-fifteen/
  web/                 # Next.js → Vercel project root
    app/
      map/             # MapLibre/Mapbox map + precinct filters
      search/          # FTS + keyword facets
      record/[uuid]/   # detail: NYPL thumb link + OCR + terms
    lib/db.ts          # @vercel/postgres queries
  worker/              # Python → Railway
    Dockerfile
    railway.toml
    seed.py
    geocode.py
    ocr.py
    mine.py
  db/
    migrations/001_init.sql
  src/                 # existing local crawl (keep)
  data/                # gitignored local corpus
  PLAN.md
```

---

## Postgres schema (v1)

```sql
-- core record (1 row per affidavit)
CREATE TABLE cof_records (
  uuid            UUID PRIMARY KEY,
  title           TEXT NOT NULL,
  address_norm    TEXT,
  title_kind      TEXT,           -- address | person | other
  precinct        TEXT,
  precinct_num    SMALLINT,       -- parsed from "Precinct 15"
  date_start      SMALLINT,
  date_end        SMALLINT,
  nypl_image_id   TEXT,
  nypl_item_url   TEXT,
  genres          TEXT[],
  host_chain      TEXT
);

-- geocode cache (dedupe by address)
CREATE TABLE cof_geocodes (
  address_norm    TEXT PRIMARY KEY,
  query           TEXT NOT NULL,
  lat             DOUBLE PRECISION,
  lng             DOUBLE PRECISION,
  geo_source      TEXT,           -- nyc_geoclient | mapbox | manual
  confidence      REAL,
  status          TEXT,           -- ok | ambiguous | failed | manual
  raw             JSONB,
  geocoded_at     TIMESTAMPTZ DEFAULT now()
);

-- OCR body
CREATE TABLE cof_documents (
  uuid            UUID PRIMARY KEY REFERENCES cof_records(uuid),
  ocr_text        TEXT,
  char_count      INT,
  quality         TEXT            -- empty | low | medium
);

-- mined terms (phase 2)
CREATE TABLE cof_terms (
  uuid            UUID REFERENCES cof_records(uuid),
  term            TEXT,
  category        TEXT,           -- vice | legal | person | place
  count           INT,
  PRIMARY KEY (uuid, term, category)
);

CREATE INDEX cof_records_precinct ON cof_records(precinct_num);
CREATE INDEX cof_records_address ON cof_records(address_norm);
CREATE INDEX cof_documents_fts ON cof_documents
  USING gin(to_tsvector('english', coalesce(ocr_text, '')));
```

**Map query:** `JOIN cof_records r ON r.address_norm = g.address_norm` → GeoJSON for MapLibre.

---

## Phase 1 — Map + geocoding

### 1a. Seed Postgres (Railway one-shot)

- Read `committee_of_fifteen_enriched.parquet` + index CSV
- Upsert 1,731 rows into `cof_records`
- Parse `precinct_num` from `"Precinct 15"` → `15`

### 1b. Geocode ~1,708 unique addresses

**Primary:** [NYC GeoClient](https://api-portal.nyc.gov/) — built for NYC streets, free with app token.

Query template:

```
{address_normalized}, Manhattan, New York, NY
```

**Fallback:** Mapbox Geocoding (if you already have a token in Vercel) — bbox restrict to lower Manhattan / 1900-era core.

**Rules:**

- Rate limit: 1 req/s (GeoClient/Nominatim etiquette)
- Store `status=ambiguous` when multiple hits — show in admin review queue later
- Historical caveat: some 1900 street names changed; flag `Front Street`, `West Street` etc. for manual pin adjustment
- **Do not** geocode on every page load — batch once, cache in `cof_geocodes`

**ETA:** ~30 min batch on Railway (with retries)

### 1c. Next.js map (Vercel)

| Piece | Choice |
|-------|--------|
| Map | **MapLibre GL** + free OSM tiles (or Mapbox if you have token) |
| Clustering | `supercluster` for 1,710 points |
| Layers | points · precinct choropleth (optional v2) · heatmap toggle |
| Filters | precinct, title search, geocode status |
| Detail | link `https://digitalcollections.nypl.org/items/{uuid}` + NYPL image URL `images.nypl.org?id={image_id}&t=w` |

**API routes (Vercel):**

- `GET /api/map` → GeoJSON FeatureCollection
- `GET /api/precincts` → counts for sidebar
- `GET /api/record/[uuid]` → record + geocode + OCR snippet

---

## Phase 2 — Text mining

Run after OCR batch completes (~1,731 files).

### 2a. Finish OCR (Railway worker)

- Port existing `src/ocr.py` into `worker/ocr.py`
- Upsert `cof_documents` with quality heuristic (`char_count < 50` → `empty`, `< 200` → `low`)

### 2b. Keyword mining (rule-based v1)

Period lexicon buckets:

| category | seed terms |
|----------|------------|
| vice | disorderly house, assignation, immoral, parlor house, resort |
| legal | affidavit, sworn, precinct, captain, arrest, summons |
| trade | saloon, hotel, lodging, keeper, proprietor |
| person | madam, inmate, frequenter (context-dependent) |

- Case-insensitive regex + word boundaries
- Store counts in `cof_terms`
- Aggregate: top terms by precinct, co-occurrence with address

### 2c. Search UI

- Postgres `to_tsvector` full-text on `ocr_text`
- Facet sidebar: precinct + mined term categories
- “Records mentioning *disorderly house* in Precinct 15”

### 2d. Optional v2 (later)

- Embeddings → Vercel AI / pgvector if extension enabled
- NER for person names (spaCy on Railway)
- LLM summaries per precinct (Vercel AI SDK, not stored wholesale)

---

## Environment variables

### Vercel (`web/`)

| Variable | Purpose |
|----------|---------|
| `POSTGRES_URL` | auto from Vercel Postgres integration |
| `POSTGRES_URL_NON_POOLING` | migrations only |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | optional, if using Mapbox tiles/geocode |
| `NEXT_PUBLIC_APP_URL` | canonical URL |

### Railway (`worker/`)

| Variable | Purpose |
|----------|---------|
| `POSTGRES_URL` | same DB as Vercel (non-pooling for writes) |
| `NYC_GEOCLIENT_APP_ID` | geocoding |
| `NYC_GEOCLIENT_APP_KEY` | geocoding |
| `MAPBOX_TOKEN` | fallback geocoder |
| `NYPL_API_TOKEN` | only if re-crawling |

---

## Build order (checklist)

- [ ] **0.** Finish local OCR (`tmux cof-ocr`) + re-run `enrich.py`
- [ ] **1.** Scaffold `web/` (Next.js 15) + `worker/` (Python 3.12)
- [ ] **2.** `db/migrations/001_init.sql` → apply to Vercel Postgres
- [ ] **3.** `worker/seed.py` → load 1,731 records
- [ ] **4.** `worker/geocode.py` → fill `cof_geocodes`
- [ ] **5.** Map page live on Vercel preview
- [ ] **6.** `worker/ocr.py` + `worker/mine.py` → documents + terms
- [ ] **7.** Search page + FTS
- [ ] **8.** Custom domain + about/provenance page (portfolio copy)

---

## Portfolio story (for the site)

1. **Discovery** — found 1,731-item NYPL archive nobody has used for data work
2. **Pipeline** — API crawl → MODS enrichment → OCR → geocode → lexicon mining
3. **Insight** — map 1900 vice affidavits by precinct; searchable primary sources
4. **Provenance** — every record links back to NYPL; rights UND noted

---

## Open decisions (pick when we scaffold)

1. **Domain name?** (e.g. `committeeoffifteen.app` or subdomain of existing site)
2. **Map tiles:** Mapbox (if you have token) vs MapLibre + OSM (free)
3. **Geocoder:** NYC GeoClient only vs GeoClient + Mapbox fallback
4. **Git host:** `tedrubin80/commitieoffifteen` ✓
5. **HF dataset:** `tedrubin80/committee-of-fifteen-dataset`
6. **Kaggle dataset:** `tedrubin80/committee-of-fifteen-nyc-vice-records`

---

## Not in scope for v1

- Re-hosting NYPL images on Vercel Blob
- User accounts / auth
- Crowdsourced manual geocode corrections UI (v2 nice-to-have)
- Real-time sync from Hetzner — one-time seed + occasional re-import
