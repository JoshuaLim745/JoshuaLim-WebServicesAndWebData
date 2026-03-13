import sys
import os
import pytest
from unittest.mock import patch
from databaseModel import Genre, Book
from router import extraFeatures

def test_genre_trends(client, db_session):
    genre = Genre(name="Sci-Fi")
    db_session.add(genre)
    db_session.commit()
    
    response = client.get("/Extra-Features/trends/book")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_suggestions_unauthorized(client):
    # Fails because it doesn't provide a Bearer token
    response = client.post("/Extra-Features/suggestions")
    assert response.status_code == 401

def test_suggestions_with_seeded_data(client, db_session):
    # 1. Setup User and Auth (Fix: Use JSON and 'email' key)
    email, pwd = "tester@test.com", "securepassword"
    client.post("/users/create", json={"email": email, "password": pwd})
    login_resp = client.post("/users/login", json={"email": email, "password": pwd})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Update Genres
    client.put("/users/update-genres", 
                json={"mode": "add", "genreName": "Fantasy"}, 
                headers=headers)
    
    # 3. Get Suggestions
    resp = client.post("/Extra-Features/suggestions", headers=headers)
    assert resp.status_code == 200

def test_crud_with_missing_csv_rating(client):
    payload = {
        "title": "The Essentials of Finance",
        "author": "Edward Fields",
        "avgRating": 0.0, # Changed from None to 0.0 to match Schema requirements
        "genreIds": []
    }
    resp = client.post("/books/", json=payload)
    assert resp.status_code == 200

@patch("router.extraFeatures.generate_ai_description") # Fix: Patch the helper function
def test_ai_description_failure(mock_gen, client):
    # Simulate API Error
    mock_gen.side_effect = Exception("API Down")
    
    # Create a book and get the dynamic ID
    create_res = client.post("/books/", json={"title": "AI Book", "author": "Robot", "avgRating": 5.0})
    book_id = create_res.json()["id"]
    
    resp = client.get(f"/Extra-Features/ai-description?book_id={book_id}")
    assert resp.status_code == 502
    assert "Gemini API Error" in resp.json()["detail"]