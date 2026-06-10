import uuid

import pytest

from tests.helpers import assert_json_response, request


@pytest.mark.parametrize("size", [1_000, 10_000])
def test_register_very_long_credentials_returns_controlled_json(size):
    credentials = {
        "username": f"long_user_{size}_{uuid.uuid4().hex}_" + ("u" * size),
        "password": "p" * size,
    }

    response = request("POST", "/register", json=credentials)
    payload = assert_json_response(response)

    assert response.status_code < 500, response.text
    if response.status_code == 201:
        assert payload == {"message": "User registered successfully"}
    else:
        assert "error" in payload
        assert payload["error"]["http_status"] == response.status_code


@pytest.mark.parametrize("size", [1_000, 10_000])
def test_login_very_long_credentials_returns_controlled_json(size):
    credentials = {
        "username": f"login_long_user_{size}_{uuid.uuid4().hex}_" + ("u" * size),
        "password": "p" * size,
    }

    register_response = request("POST", "/register", json=credentials)
    assert_json_response(register_response)
    assert register_response.status_code in {201, 409}

    response = request("POST", "/login", json=credentials)
    payload = assert_json_response(response)

    assert response.status_code < 500, response.text
    if response.status_code == 200:
        assert isinstance(payload["token"], str)
        assert payload["token"]
    else:
        assert "error" in payload
        assert payload["error"]["http_status"] == response.status_code
