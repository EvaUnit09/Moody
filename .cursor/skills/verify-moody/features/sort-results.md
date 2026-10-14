# Sort results

After a search, the user reorders the cards on this page. Sorting does not ask the server for a new list.

## Sub-features

- `sort-best` keeps the order the server returned.
- `sort-rated` orders by visible TMDB rating, highest first.
- `sort-newest` orders by visible year, newest first.
- `sort-title` orders titles A–Z.

## How to get to it (user POV)

- Run a search that shows cards. The radiogroup `Sort results` appears above the grid.
- Choose `Best match`, `Highest rated`, `Newest`, or `Title A–Z`.

## Driving it with the Cursor browser

Preconditions:

- Doctor is ok.
- A successful search with at least two cards is on screen. One recommend call is enough. Do not search again to prove sort.
- Note the title order and each card's visible year and `TMDB` rating before changing sort.

- **Default.** The radio `Best match` is checked (`aria-checked` true). Record that title order.
- **Highest rated.** Click the radio `Highest rated`. It is checked. Card order is the previous cards sorted by the visible TMDB number, larger first. A card with no `TMDB` line sorts after cards that have one.
- **Newest.** Click `Newest`. Order follows the visible year, larger first. A card with no year line sorts last.
- **Title.** Click `Title A–Z`. Titles are in locale alphabetical order.
- **No refetch.** The heading still quotes the original query. The URL `?q=` is unchanged. Do not require a new `POST /recommend` in the network log.
- **Proof.** Save `artifacts/sort-results/sorted.aria.txt` and `artifacts/sort-results/sorted.png` after `Title A–Z` or `Highest rated`. `notes.txt` names the sub-feature and entry point `Sort results`.

## Gotchas

- The radiogroup is not on the home shelf. It mounts only after a search finishes without an error. A new search unmounts it, so the next result set starts at `Best match` again.
- Sort compares missing rating or year as less than any real value, so those cards end up last for `Highest rated` and `Newest`.
- Hidden cards are already removed from the grid. Sort only the titles still on screen.
- `Best match` means the order in the latest response, not a higher rating.
