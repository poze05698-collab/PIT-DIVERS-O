import logging
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH, DATA

log = logging.getLogger("backup")
BACKUP_DIR = DATA / "backups"
KEEP_BACKUPS = 30

def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def db_is_healthy(path):
    if not Path(path).exists():
        return False
    try:
        con = sqlite3.connect(path, timeout=10)
        result = con.execute("PRAGMA integrity_check").fetchone()
        con.close()
        return bool(result and result[0] == "ok")
    except Exception:
        return False

def create_backup():
    DATA.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(DATABASE_PATH)

    if not db_is_healthy(source):
        log.warning("Banco principal ausente ou inválido; backup não criado.")
        return None

    destination = BACKUP_DIR / f"pit_diversao_{_timestamp()}.db"
    # SQLite backup API gera um snapshot consistente mesmo com WAL.
    source_con = sqlite3.connect(source, timeout=30)
    dest_con = sqlite3.connect(destination)
    try:
        source_con.backup(dest_con)
        dest_con.commit()
    finally:
        dest_con.close()
        source_con.close()

    backups = sorted(BACKUP_DIR.glob("pit_diversao_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[KEEP_BACKUPS:]:
        try:
            old.unlink()
        except OSError:
            pass

    latest = BACKUP_DIR / "latest.db"
    temp_latest = BACKUP_DIR / "latest.tmp.db"
    shutil.copy2(destination, temp_latest)
    temp_latest.replace(latest)

    log.info("Backup criado: %s", destination.name)
    return destination

def restore_if_needed():
    source = Path(DATABASE_PATH)
    if db_is_healthy(source):
        return False

    candidates = sorted(
        [p for p in BACKUP_DIR.glob("pit_diversao_*.db") if db_is_healthy(p)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    latest = BACKUP_DIR / "latest.db"
    if db_is_healthy(latest):
        candidates.insert(0, latest)

    if not candidates:
        return False

    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidates[0], source)
    log.warning("Banco restaurado automaticamente a partir de %s", candidates[0].name)
    return True
