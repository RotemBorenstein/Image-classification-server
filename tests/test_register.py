from tests.helpers import assert_error_response, request


def test_register_success(unique_credentials):
    response = request("POST", "/register", json=unique_credentials)

    assert response.status_code == 201
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json() == {"message": "User registered successfully"}


def test_register_duplicate_username_conflict(unique_credentials):
    first = request("POST", "/register", json=unique_credentials)
    second = request("POST", "/register", json=unique_credentials)

    assert first.status_code == 201
    assert_error_response(second, 409)


def test_register_missing_username_returns_400():
    response = request("POST", "/register", json={"password": "secret"})
    assert_error_response(response, 400)


def test_register_missing_password_returns_400():
    response = request("POST", "/register", json={"username": "alice"})
    assert_error_response(response, 400)


def test_register_empty_json_returns_400():
    response = request("POST", "/register", json={})
    assert_error_response(response, 400)


def test_register_rejects_non_object_json_body():
    response = request("POST", "/register", json=["alice", "secret"])
    assert_error_response(response, 400)


def test_register_rejects_non_string_username():
    response = request("POST", "/register", json={"username": ["alice"], "password": "secret"})
    assert_error_response(response, 400)


def test_register_rejects_non_json_content_type():
    response = request(
        "POST",
        "/register",
        data="username=alice&password=secret",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert_error_response(response, 400)


def test_register_malformed_json_returns_400():
    response = request(
        "POST",
        "/register",
        data="{bad json",
        headers={"Content-Type": "application/json"},
    )
    assert_error_response(response, 400)


def test_register_get_not_allowed_returns_405_json():
    response = request("GET", "/register")
    assert_error_response(response, 405)
