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


def test_logout_invalidates_token_for_protected_endpoint():
    username = "logout_token_user"
    password = "logout_token_pass"

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

    logout_response = requests.post(
        f"{BASE}/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    status_response = requests.get(
        f"{BASE}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_response.status_code == 401


def test_register_duplicate_username_returns_409():
    """רישום עם שם משתמש קיים חייב להחזיר 409"""
    username = "duplicate_user_interop"
    password = "somepassword"
    
    requests.post(f"{BASE}/register", json={"username": username, "password": password})
    r = requests.post(f"{BASE}/register", json={"username": username, "password": password})
    
    assert r.status_code == 409


def test_register_missing_fields_returns_400():
    """רישום בלי password חייב להחזיר 400"""
    r = requests.post(f"{BASE}/register", json={"username": "onlyusername"})
    assert r.status_code == 400


def test_classifier_without_token_returns_401():
    """קריאה ל-classifier בלי טוקן חייבת להחזיר 401"""
    files = {"image": ("test.png", b"fake", "image/png")}
    r = requests.post(f"{BASE}/classifier", files=files)
    assert r.status_code == 401


def test_classifier_success_response_format():
    """תשובת 200 מ-classifier חייבת להכיל matches עם name ו-score תקין"""
    import io
    from PIL import Image

    # יצירת תמונה אמיתית בזיכרון
    img = Image.new("RGB", (64, 64), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    username, password = "fmt_check_user", "fmt_check_pass"
    requests.post(f"{BASE}/register", json={"username": username, "password": password})
    token = requests.post(f"{BASE}/login", json={"username": username, "password": password}).json()["token"]

    r = requests.post(
        f"{BASE}/classifier",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("photo.png", buf, "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "matches" in body
    total_score = 0
    for match in body["matches"]:
        assert "name" in match
        assert "score" in match
        assert 0.0 < match["score"] <= 1.0
        total_score += match["score"]
    assert 0.0 <= total_score <= 1.0


def test_status_response_format_and_api_version():
    username, password = "status_fmt_user", "status_fmt_pass"
    requests.post(f"{BASE}/register", json={"username": username, "password": password})
    token = requests.post(f"{BASE}/login", json={"username": username, "password": password}).json()["token"]

    r = requests.get(f"{BASE}/status", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    body = r.json()
    assert "status" in body
    s = body["status"]
    assert "uptime" in s
    assert "processed" in s
    assert "success" in s["processed"]
    assert "fail" in s["processed"]
    assert "health" in s
    assert s["health"] in ("ok", "error")
    assert "api_version" in s
    assert s["api_version"] == 1