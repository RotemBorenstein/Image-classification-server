import requests


BASE_URL = "http://web:5000"


def request(method, path, **kwargs):
    return requests.request(method, f"{BASE_URL}{path}", timeout=10, **kwargs)


def assert_error_response(response, expected_status):
    assert response.status_code == expected_status
    assert response.headers["Content-Type"].startswith("application/json")
    payload = response.json()
    assert payload["error"]["http_status"] == expected_status
    assert isinstance(payload["error"]["message"], str)
    assert payload["error"]["message"]
    return payload
