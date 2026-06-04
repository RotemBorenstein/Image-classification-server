import io

from tests.helpers import assert_error_response, request


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_classifier_requires_authentication():
    response = request("POST", "/classifier", files={})
    assert_error_response(response, 401)


def test_classifier_rejects_missing_image(authenticated_token):
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files={},
    )
    assert_error_response(response, 400)


def test_classifier_rejects_unsupported_extension(authenticated_token):
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files={"image": ("bad.bin", io.BytesIO(b"not an image"), "application/octet-stream")},
    )
    assert_error_response(response, 400)


def test_classifier_rejects_malformed_authorization_header(authenticated_token):
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": authenticated_token},
        files={"image": ("tiny.png", io.BytesIO(PNG_1X1), "image/png")},
    )
    assert_error_response(response, 401)


def test_classifier_invalid_token_returns_401():
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": "Bearer definitely-invalid-token"},
        files={"image": ("tiny.png", io.BytesIO(PNG_1X1), "image/png")},
    )
    assert_error_response(response, 401)


def test_classifier_get_not_allowed_returns_405_json():
    response = request("GET", "/classifier")
    assert_error_response(response, 405)


def test_classifier_success_returns_matches(authenticated_token):
    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files={"image": ("tiny.png", io.BytesIO(PNG_1X1), "image/png")},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    payload = response.json()
    assert "matches" in payload
    assert isinstance(payload["matches"], list)
    assert payload["matches"]

    total_score = 0.0
    for match in payload["matches"]:
        assert isinstance(match["name"], str)
        assert match["name"]
        assert isinstance(match["score"], (int, float))
        assert 0.0 < match["score"] <= 1.0
        total_score += match["score"]

    assert 0.0 < total_score <= 1.0
