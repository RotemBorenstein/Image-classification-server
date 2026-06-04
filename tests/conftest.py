import time
import uuid

import pytest
import requests

from tests.helpers import request


@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    deadline = time.time() + 120
    last_error = None

    while time.time() < deadline:
        try:
            response = request("GET", "/")
            if response.status_code == 200:
                return
            last_error = f"unexpected status {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1)

    raise RuntimeError(f"web service did not become ready: {last_error}")


@pytest.fixture
def unique_username():
    return f"user_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def unique_credentials(unique_username):
    return {"username": unique_username, "password": f"pw_{uuid.uuid4().hex}"}


@pytest.fixture
def registered_user(unique_credentials):
    response = request("POST", "/register", json=unique_credentials)
    assert response.status_code == 201, response.text
    return unique_credentials


@pytest.fixture
def authenticated_token(registered_user):
    response = request("POST", "/login", json=registered_user)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload["token"], str)
    assert payload["token"]
    return payload["token"]


@pytest.fixture
def status_snapshot(authenticated_token):
    response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {authenticated_token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["status"]
