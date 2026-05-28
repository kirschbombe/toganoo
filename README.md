# Toganoo Collection Provenance Annotation Tool

UCLA Library · Digital Collections and Scholarship  
Dawn Childress & Tomoko Bialock

A IIIF-based annotation tool for curating provenance data from the UCLA Toganoo Collection of Esoteric Buddhism. Scholars annotate image regions in IIIF manifests, capturing structured data about provenance marks (seals, stamps, inscriptions, labels). Annotations are stored as W3C Web Annotations and exportable as TEI XML and Linked Art JSON-LD.

---

## Stack

- **Backend**: Python / FastAPI / SQLite
- **Frontend**: Vanilla JS / OpenSeadragon / Annotorious
- **Auth**: ORCID OAuth 2.0
- **Deploy**: Docker / Render

---

## Local setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd toganoo
cp .env.example .env
# Edit .env with your ORCID credentials and a random SECRET_KEY
```

### 2. ORCID OAuth credentials

Register a public API application at https://sandbox.orcid.org/developer-tools (sandbox for dev).

- Redirect URI: `http://localhost:8000/auth/callback`
- Copy the Client ID and Client Secret into `.env`

### 3. Run with Docker Compose

```bash
docker compose up --build
```

Open http://localhost:8000

### 4. Run without Docker (development)

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

---

## Deployment on Render

1. Push to GitHub
2. New Web Service → connect repo
3. Runtime: Docker
4. Environment variables: `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `SECRET_KEY`, `BASE_URL`, `HTTPS_ONLY=true`
5. Set `ORCID_SANDBOX=false` and register a production ORCID app with your Render URL as redirect URI

Render free tier spins down after inactivity — first load after idle will be slow (~30s).

### 5. Seed annotations from Hiro's TEI files

With the app running, in a separate terminal:

```bash
docker compose exec app python scripts/seed_from_tei.py
```

This imports provenance annotations from the TEI files in `data/tei/` into the database. Each seal and provenance entry becomes one annotation record attributed to Hiroyuki Ikuura. Canvas IDs and image regions are placeholders — scholars can refine them via the UI.

Run once only; the script skips volumes already seeded.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/login` | Begin ORCID OAuth |
| GET | `/auth/callback` | OAuth callback |
| GET | `/auth/logout` | Clear session |
| GET | `/auth/me` | Current user |
| GET | `/api/annotations/volume/{ark}` | Get annotations for a volume |
| POST | `/api/annotations/` | Create annotation |
| PUT | `/api/annotations/{id}` | Update annotation |
| DELETE | `/api/annotations/{id}` | Delete annotation |
| GET | `/api/manifest/proxy?url=` | Proxy IIIF manifest |
| GET | `/api/export/tei/{ark}` | Export TEI XML |
| GET | `/api/export/linked-art/{ark}` | Export Linked Art JSON-LD |
| GET | `/api/export/annotations/{ark}` | Export W3C Web Annotations |

---

## Data model

See `toganoo-data-model.md` for the full data model including field definitions, controlled vocabularies, and TEI/Linked Art serialization examples.

---

## Project structure

```
toganoo/
├── backend/
│   ├── main.py            FastAPI application
│   ├── database.py        SQLite setup
│   └── routes/
│       ├── auth.py        ORCID OAuth
│       ├── annotations.py CRUD
│       ├── manifests.py   IIIF proxy
│       └── exports.py     TEI, Linked Art, W3C Anno
├── frontend/
│   ├── index.html
│   ├── css/app.css
│   ├── js/
│   │   ├── app.js         Main application
│   │   ├── api.js         Backend API client
│   │   ├── manifest.js    IIIF manifest parser (v2 + v3)
│   │   └── form.js        Annotation form + vocabularies
│   └── data/
│       └── volumes.json   Volume metadata (generated from CSV)
├── data/
│   └── annotations.db     SQLite database (created on first run)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Open questions / next steps

1. DHII schema alignment — contact Kiyonori Nagasaki re: seal database TEI profile
2. Authority file lookup — VIAF autocomplete widget (v2)
3. K-number / J-number crosswalk — manual matching of container numbers
4. Linked Art provenance dating — handling undated ownership activities
5. `seeAlso` manifest updates — app generates updated manifests for manual PUT
6. Multi-part collection navigation — browse parent manifest, annotate volume manifests
