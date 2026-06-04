from tests.helpers import request


def test_root_serves_auth_page():
    response = request("GET", "/")

    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "Login or register" in response.text
    assert 'id="login-form"' in response.text
    assert 'id="register-form"' in response.text


def test_upload_page_is_served():
    response = request("GET", "/upload")

    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "Upload an image for classification." in response.text
    assert 'id="upload-form"' in response.text
