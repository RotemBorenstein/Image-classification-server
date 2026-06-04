import uuid

users = {}
tokens = {}


def create_user(username, password):
    if username in users:
        return False
    users[username] = password
    return True


def authenticate_user(username, password):
    return users.get(username) == password


def create_token(username):
    token = str(uuid.uuid4())
    tokens[token] = username
    return token


def verify_token(token):
    return token in tokens


def invalidate_token(token):
    if token in tokens:
        del tokens[token]