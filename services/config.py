import urllib.parse
from os import environ

import dotenv


def get_config():
    dotenv.load_dotenv()
    return {
        "status_path": environ.get("STATUS_PATH", "."),
        "be_path": environ.get("BE_PATH", "http://truhlik.local:8080"),
        "schedule_json": environ.get("SCHEDULE_JSON", ".schedule.json"),
    }

def safe_urljoin(base_url: str, path: str) -> str:
    base_url = base_url.rstrip('/') + '/'
    path = path.lstrip('/')
    return urllib.parse.urljoin(base_url, path)
