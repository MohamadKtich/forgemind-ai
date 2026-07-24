import os
import shutil
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST_DB = ROOT / "test_forgemind.db"
TEST_STORAGE = ROOT / "test_storage"
TEST_MODEL = ROOT / "ml" / "models" / "test_predictive_maintenance.joblib"
TEST_METADATA = ROOT / "ml" / "models" / "test_predictive_maintenance.metadata.json"

# Configure isolated test resources before importing the application module.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["STORAGE_DIR"] = str(TEST_STORAGE)
os.environ["PREDICTIVE_MODEL_PATH"] = str(TEST_MODEL)
os.environ["PREDICTIVE_METADATA_PATH"] = str(TEST_METADATA)
os.environ["SECRET_KEY"] = "forgemind-test-secret"
os.environ["LOCAL_RECOVERY_KEY"] = "ForgeMind-Recovery-2026"
os.environ["DEVICE_API_KEY"] = "forgemind-local-device-key"


@pytest.fixture(scope="session", autouse=True)
def clean_test_resources():
    for path in (TEST_DB, TEST_MODEL, TEST_METADATA, Path(str(TEST_DB) + "-wal"), Path(str(TEST_DB) + "-shm")):
        if path.exists():
            path.unlink()
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)
    yield
    for path in (TEST_DB, TEST_MODEL, TEST_METADATA, Path(str(TEST_DB) + "-wal"), Path(str(TEST_DB) + "-shm")):
        if path.exists():
            path.unlink()
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)


@pytest.fixture(scope="session")
def client(clean_test_resources):
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def manager_headers(client):
    response = client.post("/api/auth/login", json={"email":"manager@forgemind.ai","password":"ForgeMind#2026"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    response = client.post("/api/auth/login", json={"email":"admin@forgemind.ai","password":"ForgeMind#2026"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
