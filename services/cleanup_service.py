from pathlib import Path
import shutil
from datetime import datetime, timedelta
from config.edition import current_limits

BASE = Path(__file__).resolve().parents[1]

def ensure_dirs():
    for rel in ["data/temp", "data/cache", "data/exports/temp", "data/logs", "data/backups", "uploads"]:
        (BASE / rel).mkdir(parents=True, exist_ok=True)

def cleanup_startup():
    ensure_dirs()
    temp = BASE / "data" / "temp"
    for p in temp.glob("*"):
        if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
        else: p.unlink(missing_ok=True)
    cleanup_old_files()

def cleanup_old_files():
    limits = current_limits()
    now = datetime.now()
    for rel, days_key in [("data/cache", "cache_days"), ("data/logs", "log_days")]:
        cutoff = now - timedelta(days=limits.get(days_key, 7) or 7)
        for p in (BASE / rel).glob("*"):
            if p.is_file() and datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
                p.unlink(missing_ok=True)
    keep = limits.get("max_backup_generations", 3) or 3
    backups = sorted((BASE / "data" / "backups").glob("backup_*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
    for p in backups[keep:]:
        p.unlink(missing_ok=True)
