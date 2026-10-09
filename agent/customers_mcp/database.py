import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "customers.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


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
