def test_user_lifecycle(client):
    # 1. Create User (Still uses JSON)
    reg_response = client.post("/users/create", json={"email": "test@example.com", "password": "password123"})
    assert reg_response.status_code == 200

    # 2. Login (NOW uses Form Data 'username' and 'password')
    login_response = client.post(
        "/users/login", 
        data={"username": "test@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Read Profile (Now uses token instead of sending credentials in body)
    profile_response = client.post("/users/read", headers=headers)
    assert profile_response.status_code == 200
    assert "favoriteGenres" in profile_response.json()

    # 4. Delete User
    del_response = client.delete("/users/delete", headers=headers)
    assert del_response.status_code == 200