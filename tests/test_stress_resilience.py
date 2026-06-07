import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from tests.helpers import PNG_1X1, assert_error_response, request


RUN_STRESS = os.getenv("RUN_STRESS_TESTS") == "1"
RUN_ENVIRONMENT = os.getenv("RUN_ENVIRONMENT_TESTS") == "1"


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

        with ThreadPoolExecutor(max_workers=10) as executor:
            responses = list(executor.map(register_same_user, [credentials] * 10))

        status_codes = [response.status_code for response in responses]
        assert status_codes.count(201) == 1
        assert status_codes.count(409) == 9
        assert 500 not in status_codes


@pytest.mark.stress
@pytest.mark.skipif(not RUN_STRESS, reason="set RUN_STRESS_TESTS=1 to run stress tests")
def test_parallel_logins_issue_distinct_tokens_without_cross_invalidation(registered_user):
    def login_once():
        return request("POST", "/login", json=registered_user)

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(lambda _: login_once(), range(10)))

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
