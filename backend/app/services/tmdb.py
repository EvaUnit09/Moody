import os

from dotenv import load_dotenv

load_dotenv()

API_READ_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_READ_TOKEN}",
}
