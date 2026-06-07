from tests.helpers import (
    assert_counts_delta,
    assert_error_response,
    get_processed_counts,
    request,
)


def test_status_unauthorized_request_does_not_change_counters(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request("GET", "/status")
    assert_error_response(response, 401)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=0)


def test_status_invalid_token_does_not_change_counters(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request(
        "GET",
        "/status",
        headers={"Authorization": "Bearer definitely-invalid-token"},
    )
    assert_error_response(response, 401)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=0)


def test_status_malformed_bearer_header_does_not_change_counters(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request(
        "GET",
        "/status",
        headers={"Authorization": authenticated_token},
    )
    assert_error_response(response, 401)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=0)


def test_status_authorized_request_does_not_change_counters(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert response.status_code == 200

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=0)


def test_register_get_405_counts_as_failed_job(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request("GET", "/register")
    assert_error_response(response, 405)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_login_get_405_counts_as_failed_job(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request("GET", "/login")
    assert_error_response(response, 405)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_logout_get_405_counts_as_failed_job(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request("GET", "/logout")
    assert_error_response(response, 405)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_classifier_get_405_counts_as_failed_job(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = request("GET", "/classifier")
    assert_error_response(response, 405)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)
