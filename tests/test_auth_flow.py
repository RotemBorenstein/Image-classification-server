from tests.helpers import assert_error_response, request


def test_register_then_login_then_logout_flow(unique_credentials):
    register_response = request("POST", "/register", json=unique_credentials)
    assert register_response.status_code == 201

    login_response = request("POST", "/login", json=unique_credentials)
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    logout_response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200


def test_two_logins_issue_independent_tokens(registered_user):
    first = request("POST", "/login", json=registered_user)
    second = request("POST", "/login", json=registered_user)

    first_token = first.json()["token"]
    second_token = second.json()["token"]

    assert first_token != second_token

    first_status = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    second_status = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert first_status.status_code == 200
    assert second_status.status_code == 200


def test_logout_only_invalidates_submitted_token(registered_user):
    first = request("POST", "/login", json=registered_user)
    second = request("POST", "/login", json=registered_user)

    first_token = first.json()["token"]
    second_token = second.json()["token"]

    logout_response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert logout_response.status_code == 200

    first_status = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    second_status = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert_error_response(first_status, 401)
    assert second_status.status_code == 200
