import os
import struct
import zlib

import requests


BASE_URL = os.getenv("BASE_URL", "http://web:5000")
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def get_processed_counts(token):
    response = request(
        "GET",
        "/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text

    processed = response.json()["status"]["processed"]
    return {"success": processed["success"], "fail": processed["fail"]}


def assert_counts_delta(before, after, success=0, fail=0):
    assert after["success"] - before["success"] == success
    assert after["fail"] - before["fail"] == fail


def make_png_decompression_bomb(width=50000, height=50000):
    def chunk(tag, data):
        checksum = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_pixels = b"\x00\x00\x00\x00"
    idat = zlib.compress(raw_pixels)

    return (
        signature
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )
