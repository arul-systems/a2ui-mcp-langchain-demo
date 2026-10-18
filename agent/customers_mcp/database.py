import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_DIR = Path(__file__).parent
SCHEMA_PATH = DB_DIR / "schema.sql"


def _writable_db_dir() -> Path:
    """DB_DIR (agent/customers_mcp/) is writable in local dev, but Azure
    Functions mounts deployed code read-only, so customers.db -- gitignored,
    created fresh on first touch -- needs to live somewhere actually
    writable there instead. Probed with a real write, not just permission
    bits, since a read-only *mount* can still pass an os.access() check.
    """
    probe = DB_DIR / ".writable_probe"
    try:
        probe.touch()
        probe.unlink()
        return DB_DIR
    except OSError:
        return Path(tempfile.gettempdir())


DB_PATH = _writable_db_dir() / "customers.db"


def init_db(db_path: Path = DB_PATH) -> None:
    """(Re)create the customers table from schema.sql. Drops any existing data."""
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
