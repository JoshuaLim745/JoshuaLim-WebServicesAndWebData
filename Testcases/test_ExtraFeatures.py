import sys
import os
import pytest
from unittest.mock import patch

# 1. FORCE THE PATH AT THE VERY TOP
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. NOW IMPORT (This will now succeed)
from databaseModel import Genre, Book
from router import extraFeatures


def test_genre_trends(client, db_session):
    # Manually seed a genre and book for testing trends
    genre = Genre(name="Sci-Fi")
    db_session.add(genre)
    db_session.commit()
    
    # Check trends endpoint
    response = client.get("/Extra-Features/trends/book")
    assert response.status_code == 200
    # Even if empty, it should return a dict
    assert isinstance(response.json(), dict)

def test_suggestions_unauthorized(client):
    # Test that suggestions fail without valid credentials
    response = client.post("/Extra-Features/suggestions", json={"email": "ghost@test.com", "password": "nop"})
    assert response.status_code == 401



def test_suggestions_with_seeded_data(client, db_session):
    # 1. Setup User and Auth
    email, pwd = "tester@test.com", "securepassword"
    client.post("/users/create", json={"email": email, "password": pwd})
    login_resp = client.post("/users/login", data={"username": email, "password": pwd})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Update Genres (Protected)
    client.put("/users/update-genres", 
                json={"mode": "add", "genreName": "Fantasy"}, 
                headers=headers)
    
    # 3. Get Suggestions (Protected)
    resp = client.post("/Extra-Features/suggestions", headers=headers)
    assert resp.status_code == 200


def test_crud_with_missing_csv_rating(client):
    # ID 1288: "The Essentials of Finance...", rating is empty in CSV
    payload = {
        "title": "The Essentials of Finance",
        "author": "Edward Fields",
        "avgRating": None, # Should be handled by your Pydantic model or DB default
        "genreIds": []
    }
    resp = client.post("/books/", json=payload)
    # If your model requires a float, this should fail with 422
    # If it allows None, it should succeed.
    assert resp.status_code in [200, 422]



@patch("router.extraFeatures.get_book_description_ai")
def test_ai_description_failure(mock_gen, client):
    # Simulate API Error
    mock_gen.side_effect = Exception("API Down")
    
    # Create a book first
    client.post("/books/", json={"title": "AI Book", "author": "Robot", "avgRating": 5.0})
    
    resp = client.get("/Extra-Features/ai-description?book_id=1")
    assert resp.status_code == 502
    assert "Gemini API Error" in resp.json()["detail"]