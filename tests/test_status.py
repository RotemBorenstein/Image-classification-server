from tests.helpers import assert_error_response, request


def test_status_requires_authentication():
    response = request("GET", "/status")
    assert_error_response(response, 401)


def test_status_returns_required_shape(authenticated_token):
    response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    payload = response.json()["status"]

    assert isinstance(payload["uptime"], (int, float))
    assert payload["uptime"] >= 0
    assert payload["health"] in {"ok", "error"}
    assert payload["api_version"] == 1
    assert isinstance(payload["processed"]["success"], int)
    assert isinstance(payload["processed"]["fail"], int)


def test_status_missing_bearer_schema_returns_401(authenticated_token):
    response = request(
        "GET",
        "/status",
        headers={"Authorization": authenticated_token},
    )
    assert_error_response(response, 401)


def test_status_get_only_post_not_allowed_returns_405_json(authenticated_token):
    response = request(
        "POST",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert_error_response(response, 405)


def test_status_success_counter_increments_for_register_login_logout(authenticated_token):
    before = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    ).json()["status"]["processed"]

    credentials = {"username": "stats_user_register_login_logout", "password": "secret"}
    register_response = request("POST", "/register", json=credentials)
    assert register_response.status_code in {201, 409}

    login_response = request("POST", "/login", json=credentials)
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    logout_response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    after = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    ).json()["status"]["processed"]

    assert after["success"] >= before["success"] + 2


def test_status_fail_counter_increments_for_register_login_logout_errors(authenticated_token):
    before = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    ).json()["status"]["processed"]

    assert request("POST", "/register", json={}).status_code == 400
    assert request("POST", "/login", json={}).status_code == 400
    assert request("POST", "/logout").status_code == 401

    after = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    ).json()["status"]["processed"]

    assert after["fail"] >= before["fail"] + 3
