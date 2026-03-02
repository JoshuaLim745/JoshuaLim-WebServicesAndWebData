def test_user_lifecycle(client):
    # 1. Create User
    reg_response = client.post("/users/create", json={"email": "test@example.com", "password": "password123"})
    assert reg_response.status_code == 200
    assert reg_response.json()["email"] == "test@example.com"

    # 2. Read User (Login)
    login_response = client.post("/users/read", json={"email": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    assert "favoriteGenres" in login_response.json()

    # 3. Unauthorized Access
    bad_login = client.post("/users/read", json={"email": "test@example.com", "password": "wrongpassword"})
    assert bad_login.status_code == 401

    # 4. Delete User
    del_response = client.request("DELETE", "/users/delete", json={"email": "test@example.com", "password": "password123"})
    assert del_response.status_code == 200