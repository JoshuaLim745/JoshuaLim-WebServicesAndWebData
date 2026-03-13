import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from dotenv import load_dotenv

# Get the path to the directory above 'Testcases' (the root)
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(base_dir, ".env")

# Load the .env file from the root
load_dotenv(dotenv_path)

# 1. FIX PATHS
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import databaseModel
import seedingData
from main import app

# 2. DEFINE SQLITE ENGINE
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def db_engine():
    # Create the isolated engine
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # 3. SESSION-LEVEL PATCHING
    # We use patch.object because monkeypatch doesn't support session scope
    with patch.object(databaseModel, "engine", test_engine), \
        patch.object(seedingData, "engine", test_engine):
        
        databaseModel.Base.metadata.create_all(bind=test_engine)
        
        # 4. SEED: Pass the specific engine to your migration script
        seedingData.run_migration(target_engine=test_engine)
        
        yield test_engine
        databaseModel.Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback() 
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    from databaseModel import get_db
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    email, pwd = "test@example.com", "password123"
    client.post("/users/create", json={"email": email, "password": pwd})
    resp = client.post("/users/login", data={"username": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}