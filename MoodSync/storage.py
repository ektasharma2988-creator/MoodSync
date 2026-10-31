
import json
import os

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default

def save_json(filename, data):
    folder = os.path.dirname(filename)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
