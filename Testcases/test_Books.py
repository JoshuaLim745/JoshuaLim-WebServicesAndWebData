import pytest
import csv
from main import app
from fastapi.testclient import TestClient

# Helper to load data from your specific CSV for test cases
def get_csv_data():
    try:
        with open('filtered_google_books.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [row for row in reader][:5] 
    except FileNotFoundError:
        return []

@pytest.mark.parametrize("book_data", get_csv_data())
def test_book_crud_lifecycle(client, book_data):
    """
    Tests Create, Read, and Delete using books from filtered_google_books.csv
    """
    # 1. CREATE
    payload = {
        "title": book_data['title'],
        "author": book_data['author'],
        "avgRating": float(book_data['rating']) if book_data['rating'] else 0.0,
        "genreIds": [] 
    }
    create_resp = client.post("/books/", json=payload)
    assert create_resp.status_code == 200
    book_id = create_resp.json()["id"]

    # 2. READ
    read_resp = client.get(f"/books/{book_id}")
    assert read_resp.status_code == 200
    assert read_resp.json()["title"] == book_data['title']

    # 3. UPDATE
    update_resp = client.put(f"/books/{book_id}?field_name=author&new_value=Updated Author")
    assert update_resp.status_code == 200
    assert client.get(f"/books/{book_id}").json()["author"] == "Updated Author"

    # 4. DELETE
    del_resp = client.delete(f"/books/{book_id}")
    assert del_resp.status_code == 200
    assert client.get(f"/books/{book_id}").status_code == 404


def test_book_crud_and_rating(client):
    # 1. Setup: Create Book
    book_resp = client.post("/books/", json={
        "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "avgRating": 0.0, "genreIds": []
    })
    book_id = book_resp.json()["id"]

    # 2. Setup: Create User & Get Token (Fix: Use JSON and 'email' key)
    client.post("/users/create", json={"email": "rater@test.com", "password": "password"})
    login_resp = client.post("/users/login", json={"email": "rater@test.com", "password": "password"})
    
    assert "access_token" in login_resp.json(), f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Rate the Book
    rating_data = {"bookId": book_id, "rating": 5.0}
    rate_res = client.post("/books/ratings/rate", json=rating_data, headers=headers)
    assert rate_res.status_code == 200


def test_dynamic_update_and_rating(client):
    # Setup: Create User and Login
    client.post("/users/create", json={"email": "critic@test.com", "password": "password"})
    login_resp = client.post("/users/login", json={"email": "critic@test.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    book_resp = client.post("/books/", json={
        "title": "Test Book", "author": "Author A", "avgRating": 0.0, "genreIds": []
    })
    book_id = book_resp.json()["id"]

    # Test Rating
    resp = client.post("/books/ratings/rate", 
                        json={"bookId": book_id, "rating": 5.0}, 
                        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Rating updated"