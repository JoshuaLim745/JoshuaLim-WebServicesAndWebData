import pytest
from seedingData import seed_test_database # Import your helper
from fastapi.testclient import TestClient
from sqlalchemy import create_url, create_engine
from sqlalchemy.orm import sessionmaker
from databaseModel import Base, get_db
from main import app # Assuming your FastAPI app is here

# Use an in-memory SQLite DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    # Setup: Create tables in SQLite
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # NEW: Inject the CSV data into the temp database
    seed_test_database(session)
    
    try:
        yield session # This is where the test happens
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine) # Cleanup