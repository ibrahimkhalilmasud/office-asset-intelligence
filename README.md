# Office Asset Intelligence

A FastAPI + PostgreSQL office asset management platform with enterprise dashboard support.

## Features

- Asset registration and lifecycle tracking
- QR/Barcode scanning endpoint
- Employee assignment management
- Warranty, depreciation, repair, and lost asset tracking
- Vendor management
- AI endpoints for replacement timeline, unusual movement detection, and procurement recommendations
- Dashboard analytics (department usage, cost analysis, maintenance history)
- PDF export for asset inventories
- Audit logs and multi-office support

## Backend Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set PostgreSQL in production via:

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/office_assets"
```

Default local fallback uses SQLite for quick start and tests.

## Frontend

Open `/home/runner/work/office-asset-intelligence/office-asset-intelligence/frontend/index.html` in a browser while API is running at `http://127.0.0.1:8000`.

## Test

```bash
pytest -q
```
