from tests.helpers import assert_error_response, request


def test_logout_success(authenticated_token):
    response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json() == {"message": "Logged out successfully"}


def test_logout_missing_authorization_header_returns_401():
    response = request("POST", "/logout")
    assert_error_response(response, 401)


def test_logout_malformed_authorization_header_returns_401(authenticated_token):
    response = request(
        "POST",
        "/logout",
        headers={"Authorization": authenticated_token},
    )
    assert_error_response(response, 401)


def test_logout_invalid_token_returns_401():
    response = request(
        "POST",
        "/logout",
        headers={"Authorization": "Bearer definitely-invalid-token"},
    )
    assert_error_response(response, 401)


def test_logout_invalidates_token_for_protected_endpoints(authenticated_token):
    logout_response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert logout_response.status_code == 200

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert_error_response(status_response, 401)


def test_logout_get_not_allowed_returns_405_json():
    response = request("GET", "/logout")
    assert_error_response(response, 405)
