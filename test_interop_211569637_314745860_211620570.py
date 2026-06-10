import requests

BASE = "http://web:5000"



def test_classifier_rejects_fake_png_content():
    requests.post(
        f"{BASE}/register",
        json={"username": "fakepng_user", "password": "fakepng_pass"},
    )
    login_response = requests.post(
        f"{BASE}/login",
        json={"username": "fakepng_user", "password": "fakepng_pass"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    files = {"image": ("bad.png", b"not a real png", "image/png")}
    response = requests.post(
        f"{BASE}/classifier",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )

    assert response.status_code == 400


def login_wrong_password():
    username = "wrong_password_user"
    correct_password = "correct_pass"
    wrong_password = "wrong_pass"

    requests.post(
        f"{BASE}/register",
        json={"username": username, "password": correct_password},
    )

    return requests.post(
        f"{BASE}/login",
        json={"username": username, "password": wrong_password},
    )

def test_error_format():
    r = login_wrong_password()
    body = r.json()

    assert "error" in body
    assert "http_status" in body["error"]
    assert "message" in body["error"]
    assert body["error"]["http_status"] == r.status_code


def test_status_auth_error_does_not_change_processed_counters():
    username = "status_counter_user"
    password = "status_counter_pass"

    requests.post(
        f"{BASE}/register",
        json={"username": username, "password": password},
    )
    login_response = requests.post(
        f"{BASE}/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    before_response = requests.get(
        f"{BASE}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert before_response.status_code == 200
    before_processed = before_response.json()["status"]["processed"]

    unauthorized_response = requests.get(f"{BASE}/status")
    assert unauthorized_response.status_code == 401

    after_response = requests.get(
        f"{BASE}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_response.status_code == 200
    after_processed = after_response.json()["status"]["processed"]

    assert after_processed["success"] == before_processed["success"]
    assert after_processed["fail"] == before_processed["fail"]
