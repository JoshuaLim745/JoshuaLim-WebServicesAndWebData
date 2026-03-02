def test_book_crud_and_rating(client):
    # 1. Create a Book
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "avgRating": 0.0,
        "genreIds": []
    }
    response = client.post("/books/", json=book_data)
    assert response.status_code == 200
    book_id = response.json()["id"]

    # 2. Update a Field
    update_res = client.put(f"/books/{book_id}?field_name=author&new_value=Fitzgerald")
    assert update_res.status_code == 200

    # 3. Rate the Book (Requires a User)
    client.post("/users/create", json={"email": "rater@test.com", "password": "password"})
    
    rating_data = {
        "email": "rater@test.com",
        "password": "password",
        "bookId": book_id,
        "rating": 5.0
    }
    rate_res = client.post("/books/rate", json=rating_data)
    assert rate_res.status_code == 200
    assert rate_res.json()["newBookAverage"] == 5.0