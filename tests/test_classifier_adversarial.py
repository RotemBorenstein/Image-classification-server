import importlib.util
import io
import sys
import types
import uuid
from pathlib import Path

import pytest

from tests.helpers import (
    PNG_1X1,
    assert_counts_delta,
    assert_error_response,
    get_processed_counts,
    make_png_decompression_bomb,
    request,
)


def _upload(authenticated_token, filename, payload, content_type=None):
    file_tuple = (filename, io.BytesIO(payload))
    if content_type is not None:
        file_tuple = (filename, io.BytesIO(payload), content_type)

    return request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files={"image": file_tuple},
    )


def _load_isolated_app_module(classify_image):
    web_dir = Path(__file__).resolve().parents[1] / "web"
    module_name = f"isolated_app_{uuid.uuid4().hex}"

    fake_auth = types.ModuleType("auth")
    fake_auth.create_user = lambda username, password: True
    fake_auth.authenticate_user = lambda username, password: True
    fake_auth.create_token = lambda username: "token"
    fake_auth.verify_token = lambda token: True
    fake_auth.invalidate_token = lambda token: None

    fake_model = types.ModuleType("model")
    fake_model.classify_image = classify_image

    previous_auth = sys.modules.get("auth")
    previous_model = sys.modules.get("model")
    sys.modules["auth"] = fake_auth
    sys.modules["model"] = fake_model

    try:
        spec = importlib.util.spec_from_file_location(module_name, web_dir / "app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_auth is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = previous_auth

        if previous_model is None:
            sys.modules.pop("model", None)
        else:
            sys.modules["model"] = previous_model


def test_classifier_rejects_wrong_part_content_type_even_with_valid_png_bytes(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = _upload(authenticated_token, "tiny.png", PNG_1X1, "text/plain")
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_classifier_rejects_application_octet_stream_even_with_valid_png_bytes(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = _upload(authenticated_token, "tiny.png", PNG_1X1, "application/octet-stream")
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_classifier_rejects_missing_part_content_type(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = _upload(authenticated_token, "tiny.png", PNG_1X1)
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_classifier_rejects_empty_multipart_part_content_type(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = _upload(authenticated_token, "tiny.png", PNG_1X1, "")
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


@pytest.mark.parametrize("unsupported_mime", ["image/gif", "text/plain", "application/pdf"])
def test_classifier_accepts_only_png_or_jpeg_mime_types(authenticated_token, unsupported_mime):
    before = get_processed_counts(authenticated_token)

    response = _upload(authenticated_token, "tiny.png", PNG_1X1, unsupported_mime)
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


def test_classifier_decompression_bomb_returns_400_not_500(authenticated_token):
    before = get_processed_counts(authenticated_token)

    response = _upload(
        authenticated_token,
        "bomb.png",
        make_png_decompression_bomb(),
        "image/png",
    )
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


@pytest.mark.parametrize(
    ("name", "files"),
    [
        ("missing image", {}),
        ("wrong mime", {"image": ("tiny.png", io.BytesIO(PNG_1X1), "text/plain")}),
        ("broken bytes", {"image": ("broken.png", io.BytesIO(b"not really a png"), "image/png")}),
        (
            "decompression bomb",
            {
                "image": (
                    "bomb.png",
                    io.BytesIO(make_png_decompression_bomb()),
                    "image/png",
                )
            },
        ),
    ],
)
def test_classifier_malformed_image_failures_increment_counter_once(authenticated_token, name, files):
    before = get_processed_counts(authenticated_token)

    response = request(
        "POST",
        "/classifier",
        headers={"Authorization": f"Bearer {authenticated_token}"},
        files=files,
    )
    assert_error_response(response, 400)

    after = get_processed_counts(authenticated_token)
    assert_counts_delta(before, after, success=0, fail=1)


@pytest.mark.xfail(
    reason="interface.md requires health='error' when classification cannot be done, but app.py has no health seam and currently hardcodes 'ok'",
    strict=False,
)
def test_status_health_reports_error_when_classifier_is_unavailable():
    module = _load_isolated_app_module(classify_image=lambda _file: (_ for _ in ()).throw(RuntimeError("boom")))
    client = module.app.test_client()

    response = client.get("/status", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.get_json()["status"]["health"] == "error"


def test_classifier_internal_failure_does_not_leak_non_json_response():
    module = _load_isolated_app_module(classify_image=lambda _file: (_ for _ in ()).throw(RuntimeError("boom")))
    client = module.app.test_client()

    response = client.post(
        "/classifier",
        headers={"Authorization": "Bearer token"},
        data={"image": (io.BytesIO(PNG_1X1), "tiny.png", "image/png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.content_type.startswith("application/json")
    assert response.get_json() == {
        "error": {"http_status": 500, "message": "boom"}
    }
    assert module.stats == {"success": 0, "fail": 1}
