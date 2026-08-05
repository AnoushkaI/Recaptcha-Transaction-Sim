import os
import pytest
from backend.config import settings
from backend.core.db import init_db, get_db_connection


@pytest.fixture(autouse=True, scope="function")
def reset_test_database():
    """Ensure a clean database state before each test in the pytest suite."""
    init_db(settings.DATABASE_URL)
    try:
        conn = get_db_connection(settings.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE audit_log RESTART IDENTITY CASCADE;")
        conn.commit()
        conn.close()
    except Exception:
        pass
    yield
