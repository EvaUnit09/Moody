# Mood search

The user describes a mood and Moody replaces the home shelf with a short list of movies, each with a one-sentence reason. The same search runs from the textbox or a starter chip.

## Sub-features

- `search-submit` searches the words in the textbox.
- `search-chip` searches a starter mood from the home chips.
- `search-url` loads `?q=` and runs that search once on first paint.
- `search-recovery` shows starter replacements when the request fails or returns no rows.
- `search-home` uses the Moody brand button to abort and return to the shelf.

## How to get to it (user POV)

- Type in the mood textbox and press the `Search` button.
- Click a starter chip such as `Search for cozy rainy night movies`.
- Open `http://127.0.0.1:5173/?q=cozy%20rainy%20night`.
- After results, click `Share results` to copy or share that URL. The visible label is `Share`, then `Copied!` for about 2 seconds when the clipboard path runs.

## Driving it with the Cursor browser

Preconditions:

- Doctor is ok.
- Fewer than 10 recommend calls have been made from this IP in the current minute. A chip and a submit each count.
- For `search-submit` and `search-chip`, start on `http://127.0.0.1:5173/` with no `?q=`.
- Use the query `cozy rainy night` unless the sub-feature says otherwise. It is three words, so the backend embeds it as typed.

- **Textbox entry.** Fill the only textbox with `cozy rainy night`. Click the button `Search`. The button name becomes `Thinking...` and the textbox is disabled until the request finishes. The URL becomes `?q=cozy%20rainy%20night`. On success the heading reads `matches for “cozy rainy night”`, `popular right now` is gone, and at least one card shows a title and a reason sentence. The radiogroup `Sort results` is present.
- **Chip entry.** From home, click `Search for date night movies`. That chip's accessible name is the control. Success uses the same heading pattern with `date night`. This query is two words, so the backend may call query expansion before embed. Still judge the screen, not the model call.
- **URL entry.** Navigate to `http://127.0.0.1:5173/?q=cozy%20rainy%20night` in a fresh page load. The search runs without another click. The heading quotes `cozy rainy night`. Changing `?q=` with the Back button does not rerun search: there is no `popstate` handler. Do not treat a Back navigation as `search-url`.
- **Recovery.** A failed or empty response shows `Nothing quite matches that. Try one of these instead:` and buttons named `Try <mood> instead`, including `Try feel-good comfort instead`. Cards and `Sort results` are absent. Record this as recovery, not as a successful shortlist.
- **Home.** Click the button `Moody`. The URL has no `?q=`. The textbox is empty. `popular right now` is back. An in-flight `Thinking...` request must not paint results after this click.
- **Proof.** For a successful textbox search, save `artifacts/mood-search/results.aria.txt`, `artifacts/mood-search/results.png`, and `notes.txt` naming `search-submit` and entry point `textbox`. The screenshot shows `Moody` and the quoted query.

## Gotchas

- The `Search` button is disabled when the textbox is empty or a search is already running.
- The textbox placeholder rotates. Do not locate the field by placeholder text.
- `Share results` calls `navigator.share` when that exists. A cancel is ignored. Otherwise it copies the `?q=` URL and the button label becomes `Copied!`.
- Recent moods, when any exist, are chips named `Search for <mood> movies` under the label `Recent`, plus `Clear recent searches`. They call the same search as starter chips. A proof of starter chips must click a chip in the starter set (`slow & melancholic`, `date night`, `nothing heavy`, `feel-good comfort`, `mind-bending`, `cozy rainy night`, `high-energy thrill`, `smart & talky`, `nostalgic 90s/00s vibes`, `dark & atmospheric`), not a recent chip with the same name pattern.
- Rate limit responses do not use the body's `message` in the UI. The screen shows the recovery prompt because the client surfaces the HTTP status. That is `search-recovery`, and it does not prove the recommender.
- `Find more like this` on a card searches `movies like ${title}, same vibe as "<current query>"`. That is a new recommend call, not a sort.
