EDITION = "dev"

LIMITS = {
    "trial": {
        "max_orders": 20,
        "max_csv_rows": 100,
        "max_scheduler_orders": 5,
        "max_display_months": 3,
        "pdf_watermark": True,
        "excel_limited": True,
        "iqms_enabled": False,
        "auto_backup": False,
        "cache_days": 1,
        "log_days": 7,
        "max_backup_generations": 3,
        "debug": False,
    },
    "pro": {
        "max_orders": None,
        "max_csv_rows": None,
        "max_scheduler_orders": 100,
        "max_display_months": 12,
        "pdf_watermark": False,
        "excel_limited": False,
        "iqms_enabled": True,
        "auto_backup": True,
        "cache_days": 7,
        "log_days": 30,
        "max_backup_generations": 30,
        "debug": False,
    },
    "dev": {
        "max_orders": None,
        "max_csv_rows": None,
        "max_scheduler_orders": None,
        "max_display_months": None,
        "pdf_watermark": False,
        "excel_limited": False,
        "iqms_enabled": True,
        "auto_backup": True,
        "cache_days": 7,
        "log_days": 30,
        "max_backup_generations": 30,
        "debug": True,
    },
}

def current_limits():
    return LIMITS.get(EDITION, LIMITS["trial"])
