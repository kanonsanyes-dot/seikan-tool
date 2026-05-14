from pathlib import Path
import shutil

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"

def clear():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for p in CACHE_DIR.glob("*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
