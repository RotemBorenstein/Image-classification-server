from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import BadRequest
import time

from auth import (
    create_user, authenticate_user,
    create_token, verify_token, invalidate_token
)
from model import classify_image

app = Flask(__name__)

start_time = time.time()

stats = {
    "success": 0,
    "fail": 0
}


def error_response(status_code, message):
    return jsonify({"error": {"http_status": status_code, "message": message}}), status_code


def get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth[len("Bearer "):].strip()
    return token or None


def get_json_body():
    try:
        data = request.get_json()
    except BadRequest:
        return None, error_response(400, "Malformed JSON")

    if not isinstance(data, dict):
        return None, error_response(400, "Missing fields")

    return data, None


@app.errorhandler(405)
def method_not_allowed(_error):
    return error_response(405, "Unsupported method")


@app.route("/", methods=["GET"])
def auth_page():
    return render_template("auth.html")


@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    try:
        data, error = get_json_body()
        if error:
            stats["fail"] += 1
            return error

        if not data or "username" not in data or "password" not in data:
            stats["fail"] += 1
            return error_response(400, "Missing fields")

        ok = create_user(data["username"], data["password"])
        if not ok:
            stats["fail"] += 1
            return error_response(409, "User exists")

        stats["success"] += 1
        return jsonify({"message": "User registered successfully"}), 201

    except Exception:
        stats["fail"] += 1
        return error_response(500, "Internal error")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    try:
        data, error = get_json_body()
        if error:
            stats["fail"] += 1
            return error

        if not data or "username" not in data or "password" not in data:
            stats["fail"] += 1
            return error_response(400, "Missing fields")

        if not authenticate_user(data["username"], data["password"]):
            stats["fail"] += 1
            return error_response(401, "Unauthorized")

        token = create_token(data["username"])
        stats["success"] += 1

        return jsonify({"token": token}), 200

    except Exception:
        stats["fail"] += 1
        return error_response(500, "Internal error")


# ---------------- LOGOUT ----------------
@app.route("/logout", methods=["POST"])
def logout():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            stats["fail"] += 1
            return error_response(401, "Invalid token")

        invalidate_token(token)
        stats["success"] += 1

        return jsonify({"message": "Logged out successfully"}), 200

    except Exception:
        stats["fail"] += 1
        return error_response(500, "Internal error")


# ---------------- CLASSIFIER ----------------
@app.route("/classifier", methods=["POST"])
def classifier():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            stats["fail"] += 1
            return error_response(401, "Invalid token")

        if "image" not in request.files:
            stats["fail"] += 1
            return error_response(400, "Missing image")

        file = request.files["image"]

        if not file.filename.endswith((".png", ".jpeg", ".jpg")):
            stats["fail"] += 1
            return error_response(400, "Unsupported image format")

        matches = classify_image(file)

        stats["success"] += 1
        return jsonify({"matches": matches}), 200

    except Exception:
        stats["fail"] += 1
        return error_response(500, "Internal error")


# ---------------- STATUS ----------------
@app.route("/status", methods=["GET"])
def status():
    try:
        token = get_bearer_token()

        if not verify_token(token):
            stats["fail"] += 1
            return error_response(401, "Invalid token")

        uptime = time.time() - start_time

        return jsonify({
            "status": {
                "uptime": uptime,
                "processed": stats,
                "health": "ok",
                "api_version": 1
            }
        }), 200

    except Exception:
        stats["fail"] += 1
        return error_response(500, "Internal error")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
