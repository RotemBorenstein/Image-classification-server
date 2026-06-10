import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from tests.helpers import (
    PNG_1X1,
    assert_counts_delta,
    assert_error_response,
    assert_json_response,
    get_processed_counts,
    make_large_valid_png,
    request,
)


RUN_STRESS = os.getenv("RUN_STRESS_TESTS") == "1"
RUN_ENVIRONMENT = os.getenv("RUN_ENVIRONMENT_TESTS") == "1"
CORRECTNESS_WORKERS = 20
BURST_WORKERS = 500
SEQUENTIAL_ITERATIONS = 20
TOKEN_STORM_TOKENS = 20
MIXED_BURST_OPERATIONS = 500
INVALID_BURST_OPERATIONS = 500
LOGIN_BURST_OPERATIONS = 500


def _call_and_capture(fn):
    try:
        response = fn()
        payload = assert_json_response(response)
        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "payload": payload,
            "transport_error": None,
        }
    except Exception as exc:
        return {
            "status_code": None,
            "content_type": None,
            "payload": None,
            "transport_error": str(exc),
        }


def _assert_burst_results(results, allowed_statuses):
    assert results
    assert all(result["transport_error"] is None for result in results), results

    for result in results:
        assert result["status_code"] in allowed_statuses, result
        assert isinstance(result["payload"], dict), result
        if result["status_code"] >= 400:
            assert "error" in result["payload"], result
            assert result["payload"]["error"]["http_status"] == result["status_code"], result


def _make_login_request(credentials):
    return request("POST", "/login", json=credentials)


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_concurrent_duplicate_register_only_allows_one_success():
    def register_same_user(credentials):
        return request("POST", "/register", json=credentials)

    for round_index in range(20):
        credentials = {
            "username": f"concurrent_register_{round_index}_{uuid.uuid4().hex[:8]}",
            "password": "secret",
        }

        with ThreadPoolExecutor(max_workers=CORRECTNESS_WORKERS) as executor:
            responses = list(executor.map(register_same_user, [credentials] * CORRECTNESS_WORKERS))

        status_codes = [response.status_code for response in responses]
        assert status_codes.count(201) == 1
        assert status_codes.count(409) == CORRECTNESS_WORKERS - 1
        assert 500 not in status_codes


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_parallel_logins_issue_distinct_tokens_without_cross_invalidation(registered_user):
    def login_once():
        return request("POST", "/login", json=registered_user)

    with ThreadPoolExecutor(max_workers=CORRECTNESS_WORKERS) as executor:
        responses = list(executor.map(lambda _: login_once(), range(CORRECTNESS_WORKERS)))

    tokens = []
    for response in responses:
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload["token"], str)
        assert payload["token"]
        tokens.append(payload["token"])

    assert len(tokens) == len(set(tokens))

    logout_response = request(
        "POST",
        "/logout",
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert logout_response.status_code == 200

    first_status = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert_error_response(first_status, 401)

    for token in tokens[1:]:
        response = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_many_sequential_classify_requests_keep_service_available(authenticated_token):
    before = get_processed_counts(authenticated_token)
    successes = 0

    for _ in range(SEQUENTIAL_ITERATIONS):
        response = request(
            "POST",
            "/classifier",
            headers={"Authorization": f"Bearer {authenticated_token}"},
            files={"image": ("tiny.png", io.BytesIO(PNG_1X1), "image/png")},
        )
        payload = assert_json_response(response, {200, 400, 500})
        if response.status_code == 200:
            successes += 1
            assert isinstance(payload["matches"], list)
            assert payload["matches"]
        else:
            assert payload["error"]["http_status"] == response.status_code

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert status_response.status_code == 200

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=successes, fail=SEQUENTIAL_ITERATIONS - successes)


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_repeated_login_logout_churn_keeps_tokens_consistent(registered_user):
    for _ in range(SEQUENTIAL_ITERATIONS):
        login_response = request("POST", "/login", json=registered_user)
        payload = assert_json_response(login_response, {200})
        token = payload["token"]

        status_response = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.status_code == 200

        logout_response = request(
            "POST",
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_json_response(logout_response, {200})

        invalidated_status = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_error_response(invalidated_status, 401)


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_token_storm_keeps_sessions_isolated(registered_user):
    tokens = []
    for _ in range(TOKEN_STORM_TOKENS):
        response = request("POST", "/login", json=registered_user)
        payload = assert_json_response(response, {200})
        tokens.append(payload["token"])

    assert len(tokens) == len(set(tokens))

    retired_tokens = tokens[: TOKEN_STORM_TOKENS // 2]
    surviving_tokens = tokens[TOKEN_STORM_TOKENS // 2 :]

    for token in retired_tokens:
        logout_response = request(
            "POST",
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_json_response(logout_response, {200})

    for token in retired_tokens:
        status_response = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_error_response(status_response, 401)

    for token in surviving_tokens:
        status_response = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.status_code == 200

    for token in surviving_tokens:
        logout_response = request(
            "POST",
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_json_response(logout_response, {200})

    for token in tokens:
        status_response = request(
            "GET",
            "/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert_error_response(status_response, 401)


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_concurrent_mixed_requests_remain_well_formed(registered_user):
    login_token = request("POST", "/login", json=registered_user).json()["token"]

    def mixed_call(index):
        operation = index % 4
        if operation == 0:
            return request(
                "GET",
                "/status",
                headers={"Authorization": f"Bearer {login_token}"},
            )
        if operation == 1:
            return request(
                "POST",
                "/logout",
                headers={"Authorization": "Bearer definitely-invalid-token"},
            )
        if operation == 2:
            return request(
                "POST",
                "/classifier",
                headers={"Authorization": f"Bearer {login_token}"},
                files={"image": ("bad.bin", io.BytesIO(b"not an image"), "application/octet-stream")},
            )
        return request("POST", "/login", json=registered_user)

    with ThreadPoolExecutor(max_workers=CORRECTNESS_WORKERS) as executor:
        results = list(executor.map(lambda index: _call_and_capture(lambda: mixed_call(index)), range(CORRECTNESS_WORKERS)))

    _assert_burst_results(results, {200, 400, 401})

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert status_response.status_code == 200


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_invalid_request_flood_does_not_break_service(authenticated_token):
    for _ in range(100):
        classifier_response = request(
            "POST",
            "/classifier",
            headers={"Authorization": f"Bearer {authenticated_token}"},
            files={"image": ("bad.bin", io.BytesIO(b"not an image"), "application/octet-stream")},
        )
        assert classifier_response.status_code in {400, 401}
        assert classifier_response.headers["Content-Type"].startswith("application/json")
        assert classifier_response.json()

        logout_response = request(
            "POST",
            "/logout",
            headers={"Authorization": "Bearer definitely-invalid-token"},
        )
        assert logout_response.status_code == 401
        assert logout_response.headers["Content-Type"].startswith("application/json")
        assert logout_response.json()

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert status_response.status_code == 200


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_large_valid_image_upload_returns_controlled_json(authenticated_token):
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files={"image": ("large.png", io.BytesIO(make_large_valid_png()), "image/png")},
    )
    payload = assert_json_response(response, {200, 400, 500})

    if response.status_code == 200:
        assert isinstance(payload["matches"], list)
        assert payload["matches"]
    else:
        assert payload["error"]["http_status"] == response.status_code


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_mixed_request_burst_with_500_concurrency_keeps_service_alive(registered_user):
    base_login = request("POST", "/login", json=registered_user)
    base_token = assert_json_response(base_login, {200})["token"]

    def burst_call(index):
        operation = index % 4
        if operation == 0:
            return request(
                "GET",
                "/status",
                headers={"Authorization": f"Bearer {base_token}"},
            )
        if operation == 1:
            return request(
                "POST",
                "/logout",
                headers={"Authorization": "Bearer definitely-invalid-token"},
            )
        if operation == 2:
            return request(
                "POST",
                "/classifier",
                headers={"Authorization": f"Bearer {base_token}"},
                files={"image": ("bad.bin", io.BytesIO(b"not an image"), "application/octet-stream")},
            )
        return request("POST", "/login", json=registered_user)

    with ThreadPoolExecutor(max_workers=BURST_WORKERS) as executor:
        results = list(executor.map(lambda index: _call_and_capture(lambda: burst_call(index)), range(MIXED_BURST_OPERATIONS)))

    _assert_burst_results(results, {200, 400, 401})

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {base_token}"},
    )
    assert status_response.status_code == 200


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_invalid_classifier_burst_with_500_concurrency_keeps_service_alive(authenticated_token):
    def invalid_classifier_call():
        return request(
            "POST",
            "/classifier",
            headers={"Authorization": f"Bearer {authenticated_token}"},
            files={"image": ("bad.bin", io.BytesIO(b"not an image"), "application/octet-stream")},
        )

    with ThreadPoolExecutor(max_workers=BURST_WORKERS) as executor:
        results = list(executor.map(lambda _: _call_and_capture(invalid_classifier_call), range(INVALID_BURST_OPERATIONS)))

    _assert_burst_results(results, {400, 401})

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert status_response.status_code == 200


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_login_burst_with_500_concurrency_returns_controlled_json(registered_user):
    with ThreadPoolExecutor(max_workers=BURST_WORKERS) as executor:
        results = list(
            executor.map(
                lambda _: _call_and_capture(lambda: _make_login_request(registered_user)),
                range(LOGIN_BURST_OPERATIONS),
            )
        )

    _assert_burst_results(results, {200, 400, 401})

    tokens = [
        result["payload"]["token"]
        for result in results
        if result["status_code"] == 200 and "token" in result["payload"]
    ]
    assert tokens

    status_response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert status_response.status_code == 200


@pytest.mark.environment
@pytest.mark.skipif(not RUN_ENVIRONMENT, reason="set RUN_ENVIRONMENT_TESTS=1 to run environment tests")
def test_cold_start_without_model_download_reports_unhealthy_instead_of_crashing():
    offline_base_url = os.getenv("OFFLINE_BASE_URL", "http://web-offline:5000")
    credentials = {
        "username": f"offline_probe_{uuid.uuid4().hex[:8]}",
        "password": "secret",
    }

    register_response = requests.post(
        f"{offline_base_url}/register",
        json=credentials,
        timeout=10,
    )
    assert register_response.status_code == 201, register_response.text

    login_response = requests.post(
        f"{offline_base_url}/login",
        json=credentials,
        timeout=10,
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["token"]

    status_response = requests.get(
        f"{offline_base_url}/status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    assert status_response.status_code == 200, status_response.text
    payload = status_response.json()["status"]
    assert payload["health"] == "error"
