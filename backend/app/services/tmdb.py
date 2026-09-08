import os

from dotenv import load_dotenv

load_dotenv()

API_READ_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_READ_TOKEN}",
}

MIN_VOTE_AVERAGE = 5.0

GENRE_MAP: dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


def genre_names(genre_ids: list[int]) -> list[str]:
    return [GENRE_MAP[gid] for gid in genre_ids if gid in GENRE_MAP]
