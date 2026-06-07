from tests.helpers import assert_error_response, request


def test_login_success_returns_token(registered_user):
    response = request("POST", "/login", json=registered_user)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    payload = response.json()
    assert isinstance(payload["token"], str)
    assert payload["token"]


def test_login_unknown_user_returns_401(unique_credentials):
    response = request("POST", "/login", json=unique_credentials)
    assert_error_response(response, 401)


def test_login_wrong_password_returns_401(registered_user):
    response = request(
        "POST",
        "/login",
        json={"username": registered_user["username"], "password": "wrong-password"},
    )
    assert_error_response(response, 401)


def test_login_missing_username_returns_400():
    response = request("POST", "/login", json={"password": "secret"})
    assert_error_response(response, 400)


def test_login_missing_password_returns_400():
    response = request("POST", "/login", json={"username": "alice"})
    assert_error_response(response, 400)


def test_login_empty_json_returns_400():
    response = request("POST", "/login", json={})
    assert_error_response(response, 400)


def test_login_rejects_non_object_json_body():
    response = request("POST", "/login", json=["alice", "secret"])
    assert_error_response(response, 400)


def test_login_rejects_non_string_password():
    response = request("POST", "/login", json={"username": "alice", "password": {"value": "secret"}})
    assert_error_response(response, 400)


def test_login_rejects_non_json_content_type():
    response = request(
        "POST",
        "/login",
        data="username=alice&password=secret",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert_error_response(response, 400)


def test_login_malformed_json_returns_400():
    response = request(
        "POST",
        "/login",
        data="{bad json",
        headers={"Content-Type": "application/json"},
    )
    assert_error_response(response, 400)


def test_login_get_not_allowed_returns_405_json():
    response = request("GET", "/login")
    assert_error_response(response, 405)


def test_login_token_can_access_protected_status(registered_user):
    login_response = request("POST", "/login", json=registered_user)
    token = login_response.json()["token"]

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert status_response.status_code == 200
    payload = status_response.json()["status"]
    assert isinstance(payload["uptime"], (int, float))
    assert payload["api_version"] == 1
