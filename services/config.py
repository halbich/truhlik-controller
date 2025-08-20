from os import environ

import dotenv


def get_config():
    dotenv.load_dotenv()
    return {
        "status_path": environ.get("STATUS_PATH", "."),
    }