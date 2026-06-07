import threading
import uuid

users = {}
tokens = {}
state_lock = threading.RLock()


def create_user(username, password):
    with state_lock:
        if username in users:
            return False
        users[username] = password
        return True


def authenticate_user(username, password):
    with state_lock:
        return users.get(username) == password


def create_token(username):
    token = str(uuid.uuid4())
    with state_lock:
        tokens[token] = username
    return token


def verify_token(token):
    with state_lock:
        return token in tokens


def invalidate_token(token):
    with state_lock:
        if token in tokens:
            del tokens[token]
