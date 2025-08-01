import json
import hashlib

def load_users(path="users.json"):
    with open(path, "r") as f:
        return json.load(f)

def verify_user(username, password, users):
    # hashed = hashlib.sha256(password.encode()).hexdigest()
    return users.get(username) == password
