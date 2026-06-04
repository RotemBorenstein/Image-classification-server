import requests

BASE = "http://web:5000"


def test_register_missing_fields():
    r = requests.post(f"{BASE}/register", json={})
    assert r.status_code == 400


def test_login_wrong_user():
    r = requests.post(f"{BASE}/login", json={
        "username": "x",
        "password": "y"
    })
    assert r.status_code in [401, 400]


def test_classifier_no_token():
    r = requests.post(f"{BASE}/classifier")
    assert r.status_code == 401


def test_status_requires_auth():
    r = requests.get(f"{BASE}/status")
    assert r.status_code == 401


def test_logout_flow():
    r = requests.post(f"{BASE}/register", json={"username": "t", "password": "p"})
    r = requests.post(f"{BASE}/login", json={"username": "t", "password": "p"})
    token = r.json()["token"]

    r2 = requests.post(f"{BASE}/logout", headers={
        "Authorization": f"Bearer {token}"
    })

    assert r2.status_code in [200, 401]