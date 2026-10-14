# Popular shelf

On the home screen, Moody shows a carousel of movies that are popular right now. The user can scroll it. The shelf goes away once a search starts.

## Sub-features

- `popular-render` shows the shelf heading and at least one catalog title after load.
- `popular-scroll` moves the carousel with the arrow buttons and keeps the shelf on screen.
- `popular-hide-on-search` removes the shelf after a mood search starts. That search spends a `/recommend` request.

## How to get to it (user POV)

- Open `http://127.0.0.1:5173` with no `?q=` parameter.
- Click the `Moody` brand button after a search. That returns home and shows the shelf again.

## Driving it with the Cursor browser

Preconditions:

- `moody-verify.sh doctor` reports ok, including `popular=` of at least 1.
- The URL is `http://127.0.0.1:5173/` with no query string.
- You have not started a search in this page load.

- **Home entry.** Navigate to `http://127.0.0.1:5173/`. The button `Moody` and the button `Open watchlist` are present. The heading `popular right now` is visible. Buttons `Scroll left` and `Scroll right` are visible. Sixteen poster links are in the carousel. Those links have empty accessible names. Read titles from each `img` alt (it ends with ` poster`) or from `.card-title`. At least one title is non-empty.
- **Catalog match.** `curl -s http://127.0.0.1:8000/popular` and save the body to `artifacts/popular-shelf/popular.json`. A title from the alt text or `.card-title` appears in that JSON `results` array. The accessibility snapshot alone does not contain the titles.
- **Scroll.** Click `Scroll right`. The heading `popular right now` remains, and `Scroll left` and `Scroll right` remain. The shelf does not navigate to a movie page.
- **Proof.** Save the snapshot to `artifacts/popular-shelf/home.aria.txt` and a screenshot to `artifacts/popular-shelf/home.png`. Write `notes.txt` with feature id `popular-render` and entry point `home`. The screenshot shows `Moody` and `popular right now`.

## Gotchas

- Carousel cards do not include `Add to watchlist` or `Pass on this recommendation`. Those controls exist on search results only.
- The shelf paints from `movierec:popular-cache` when that localStorage entry is under 10 minutes old, then refetches `GET /popular`. Wait until a title from the fresh `/popular` body is on screen before capturing proof.
- If `/popular` failed and there was no usable cache, the carousel is absent. That is a failed `popular-render`, not an empty success.
- Auto-advance moves one viewport about every 4 seconds unless the pointer is over the carousel or the browser prefers reduced motion. An arrow click waits another 4 seconds before auto-advance. At either end the next step wraps.
- Poster images load from `image.tmdb.org`. A broken image with the right alt text still counts as that title.
- Clicking a poster opens `https://www.themoviedb.org/movie/<tmdb_id>` in a new tab. Do not follow it for this journey.
- Starting a search hides the shelf. Prove `popular-hide-on-search` only when you can spend a recommend request. A missing shelf before any search is a failure, not that sub-feature.
