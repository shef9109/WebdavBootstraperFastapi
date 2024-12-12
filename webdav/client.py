import logging
import os

from dotenv import load_dotenv
from webdav3.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

WEBDAV_OPTIONS = {
    'webdav_hostname': os.getenv("WEBDAV_HOSTNAME", "http://127.0.0.1:8081/"),
    'webdav_login': os.getenv("WEBDAV_LOGIN", "user1"),
    'webdav_password': os.getenv("WEBDAV_PASSWORD", "password1"),
}


def get_webdav_client() -> Client:
    client = Client(WEBDAV_OPTIONS)
    try:
        if not client.check():
            logger.error("Не удалось подключиться к WebDAV-серверу.")
            raise ConnectionError("WebDAV сервер недоступен.")
        logger.info("Успешное подключение к WebDAV-серверу.")
    except Exception as e:
        logger.exception("Ошибка при подключении к WebDAV-серверу.")
        raise e
    return client
