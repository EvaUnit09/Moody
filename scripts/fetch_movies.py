import httpx, os, json, time
from dotenv import load_dotenv

load_dotenv()
API_READ_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")
URL = "https://api.themoviedb.org/3/discover/movie"

headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_READ_TOKEN}"
}


def get_all_movies():
    url = "https://api.themoviedb.org/3/discover/movie"
    all_movies = []
    for page in range(1, 11):
        params = {"sort_by": "popularity.desc", "page": page}
        resp = httpx.get(url, headers=headers, params=params)
        all_movies.extend(resp.json()["results"])

    with open("raw_movies.json", "w") as f:
        json.dump(all_movies, f, indent=2)

    print(f"Saved {len(all_movies)} movies")

get_all_movies()




    


