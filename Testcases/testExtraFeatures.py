import pytest
from databaseModel import Genre, Book

def test_genre_trends(client, db_session):
    # Manually seed a genre and book for testing trends
    genre = Genre(name="Sci-Fi")
    db_session.add(genre)
    db_session.commit()
    
    # Check trends endpoint
    response = client.get("/Extra Features/trends/book")
    assert response.status_code == 200
    # Even if empty, it should return a dict
    assert isinstance(response.json(), dict)

def test_suggestions_unauthorized(client):
    # Test that suggestions fail without valid credentials
    response = client.post("/Extra Features/suggestions", json={"email": "ghost@test.com", "password": "nop"})
    assert response.status_code == 401





