import os
import pytest
from backend.config import settings
from backend.core.db import init_db

@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    """Ensure a clean database state for pytest suite."""
    db_file = settings.DATABASE_PATH
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    init_db(db_file)
    yield
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
