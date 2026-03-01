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

# ------------ Create testcase -----------

def test_create_user_success(client):
    response = client.post("/users/create", json={"email": "new@test.com", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@test.com"

def test_create_user_duplicate(client):
    client.post("/users/create", json={"email": "dup@test.com", "password": "password123"})
    response = client.post("/users/create", json={"email": "dup@test.com", "password": "newpassword"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_create_user_invalid_datatype(client):
    # Testing Pydantic validation for email and types
    response = client.post("/users/create", json={"email": "not-an-email", "password": 12345})
    assert response.status_code == 422 # Unprocessable Entity


# ------------ Read testcase -----------

@pytest.mark.parametrize("email, password, expected_status", [
    ("valid@test.com", "wrong_pass", 401),   # Correct email, incorrect pass
    ("wrong@test.com", "correct_pass", 401), # Incorrect email, correct pass
    ("wrong@test.com", "wrong_pass", 401),   # Both incorrect
])
def test_read_user_failures(client, email, password, expected_status):
    client.post("/users/create", json={"email": "valid@test.com", "password": "correct_pass"})
    response = client.post("/users/read", json={"email": email, "password": password})
    assert response.status_code == expected_status

def test_read_user_success(client):
    client.post("/users/create", json={"email": "valid@test.com", "password": "correct_pass"})
    response = client.post("/users/read", json={"email": "valid@test.com", "password": "correct_pass"})
    assert response.status_code == 200
    assert "favoriteGenres" in response.json()


# ------------ Update testcase -----------

def test_update_genre_invalid_mode(client):
    client.post("/users/create", json={"email": "t@t.com", "password": "p"})
    # Mode is neither add nor delete
    response = client.put("/users/update-genres", json={
        "email": "t@t.com", "password": "p", "mode": "invalid_mode", "genreName": "Fiction"
    })
    # Note: Your current code doesn't raise an error for bad modes, it just does nothing. 
    # You might want to add a 400 error in your logic.
    assert response.status_code == 200 

def test_update_invalid_genre(client):
    client.post("/users/create", json={"email": "t@t.com", "password": "p"})
    response = client.put("/users/update-genres", json={
        "email": "t@t.com", "password": "p", "mode": "add", "genreName": "NonExistent"
    })
    assert response.status_code == 404

def test_add_then_delete_fiction(client, db):
    # First, ensure 'Fiction' exists in the Genre table
    from databaseModel import Genre
    db.add(Genre(name="Fiction"))
    db.commit()

    client.post("/users/create", json={"email": "t@t.com", "password": "p"})
    
    # Add Fiction
    client.put("/users/update-genres", json={"email": "t@t.com", "password": "p", "mode": "add", "genreName": "Fiction"})
    # Delete Fiction
    response = client.put("/users/update-genres", json={"email": "t@t.com", "password": "p", "mode": "delete", "genreName": "Fiction"})
    
    assert "Fiction" not in response.json()["updatedGenres"]


# ------------ Delete testcase -----------

def test_delete_nonexistent_user(client):
    response = client.request("DELETE", "/users/delete", json={"email": "ghost@t.com", "password": "p"})
    assert response.status_code == 401

def test_delete_user_cascade(client, db):
    from databaseModel import Genre, User
    db.add(Genre(name="Fiction"))
    db.commit()

    user_data = {"email": "delete@test.com", "password": "password"}
    client.post("/users/create", json=user_data)
    client.put("/users/update-genres", json={**user_data, "mode": "add", "genreName": "Fiction"})

    # Delete user
    response = client.request("DELETE", "/users/delete", json=user_data)
    assert response.status_code == 200

    # Ensure user is gone from DB
    assert db.query(User).filter_by(email="delete@test.com").first() is None
    # Ensure association is gone (Cascade check)