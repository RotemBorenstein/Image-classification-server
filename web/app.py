import threading
import time

from flask import Flask, has_request_context, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from auth import (
    authenticate_user,
    create_token,
    create_user,
    invalidate_token,
    verify_token,
)
import model

app = Flask(__name__)

COUNTED_ENDPOINTS = {"/register", "/login", "/logout", "/classifier"}
SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}
MALFORMED_IMAGE_EXCEPTIONS = (
    UnidentifiedImageError,
    OSError,
    ValueError,
    Image.DecompressionBombError,
)

start_time = time.time()
stats_lock = threading.Lock()
stats = {
    "success": 0,
    "fail": 0,
}


def error_response(status_code, message):
    return jsonify({"error": {"http_status": status_code, "message": message}}), status_code


def counted_path(path=None):
    if path is not None:
        return path
    if has_request_context():
        return request.path
    return None


def record_success(path=None):
    if counted_path(path) not in COUNTED_ENDPOINTS:
        return

    with stats_lock:
        stats["success"] += 1


def record_failure(path=None):
    if counted_path(path) not in COUNTED_ENDPOINTS:
        return

    with stats_lock:
        stats["fail"] += 1


def snapshot_stats():
    with stats_lock:
        return {"success": stats["success"], "fail": stats["fail"]}


def get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth[len("Bearer "):].strip()
    return token or None


def get_json_body():
    try:
        data = request.get_json()
    except (BadRequest, UnsupportedMediaType):
        return None, error_response(400, "Malformed JSON")

    if not isinstance(data, dict):
        return None, error_response(400, "Missing fields")

    return data, None


def parse_credentials(data):
    if not data or "username" not in data or "password" not in data:
        return None, error_response(400, "Missing fields")

    username = data["username"]
    password = data["password"]

    if not isinstance(username, str) or not isinstance(password, str):
        return None, error_response(400, "Invalid field types")

    if not username or not password:
        return None, error_response(400, "Missing fields")

    return {"username": username, "password": password}, None


def classifier_health_status():
    try:
        ready = getattr(model, "can_classify", lambda: True)()
    except Exception:
        ready = False

    return "ok" if ready else "error"


@app.errorhandler(405)
def method_not_allowed(_error):
    record_failure(request.path)
    return error_response(405, "Unsupported method")


@app.route("/", methods=["GET"])
def auth_page():
    return render_template("auth.html")


@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html")


@app.route("/register", methods=["POST"])
def register():
    try:
        data, error = get_json_body()
        if error:
            record_failure()
            return error

        credentials, error = parse_credentials(data)
        if error:
            record_failure()
            return error

        ok = create_user(credentials["username"], credentials["password"])
        if not ok:
            record_failure()
            return error_response(409, "User exists")

        record_success()
        return jsonify({"message": "User registered successfully"}), 201

    except Exception:
        record_failure()
        return error_response(500, "Internal error")


@app.route("/login", methods=["POST"])
def login():
    try:
        data, error = get_json_body()
        if error:
            record_failure()
            return error

        credentials, error = parse_credentials(data)
        if error:
            record_failure()
            return error

        if not authenticate_user(credentials["username"], credentials["password"]):
            record_failure()
            return error_response(401, "Unauthorized")

        token = create_token(credentials["username"])
        record_success()
        return jsonify({"token": token}), 200

    except Exception:
        record_failure()
        return error_response(500, "Internal error")


@app.route("/logout", methods=["POST"])
def logout():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            record_failure()
            return error_response(401, "Invalid token")

        invalidate_token(token)
        record_success()
        return jsonify({"message": "Logged out successfully"}), 200

    except Exception:
        record_failure()
        return error_response(500, "Internal error")


@app.route("/classifier", methods=["POST"])
def classifier():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            record_failure()
            return error_response(401, "Invalid token")

        if "image" not in request.files:
            record_failure()
            return error_response(400, "Missing image")

        file = request.files["image"]
        if not file.filename or not file.filename.lower().endswith((".png", ".jpeg")):
            record_failure()
            return error_response(400, "Unsupported image format")

        if file.mimetype not in SUPPORTED_IMAGE_MIME_TYPES:
            record_failure()
            return error_response(400, "Unsupported image format")

        try:
            matches = model.classify_image(file)
        except MALFORMED_IMAGE_EXCEPTIONS:
            record_failure()
            return error_response(400, "Malformed image")

        record_success()
        return jsonify({"matches": matches}), 200

    except RuntimeError as exc:
        record_failure()
        message = str(exc).strip() or "Classification failed"
        return error_response(500, message)
    except Exception:
        record_failure()
        return error_response(500, "Classification failed")


@app.route("/status", methods=["GET"])
def status():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            return error_response(401, "Invalid token")

        uptime = time.time() - start_time

        return jsonify(
            {
                "status": {
                    "uptime": uptime,
                    "processed": snapshot_stats(),
                    "health": classifier_health_status(),
                    "api_version": 1,
                }
            }
        ), 200

    except Exception:
        return error_response(500, "Internal error")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
