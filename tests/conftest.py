import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "test_office_assets.db"
if DB_PATH.exists():
    DB_PATH.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")
