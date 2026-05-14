from pathlib import Path
from datetime import datetime
import zipfile
from config.edition import current_limits
from services.cleanup_service import cleanup_old_files

BASE = Path(__file__).resolve().parents[1]

def create_backup():
    backups = BASE / "data" / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    out = backups / name
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        db = BASE / "data" / "seikan.db"
        if db.exists():
            zf.write(db, arcname="seikan.db")
    cleanup_old_files()
    return out
