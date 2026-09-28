# Moody — frontend

React + TypeScript + Vite frontend for [Moody](../README.md).

## Commands

```bash
npm install
npm run dev          # local dev server, http://localhost:5173
npm run build         # typecheck + production build
npm run lint          # oxlint
npm test              # vitest, single run
npm run test:coverage # vitest with coverage report
```

Set `VITE_API_URL` in `.env.local` (see `.env.example`) to point at a running
backend — defaults to `http://localhost:8000`. The value is baked in at build
time (`import.meta.env`).

CI runs these checks on Node 24 (`.github/workflows/ci.yml`). Vitest sets
`NODE_OPTIONS=--no-experimental-webstorage` in `vite.config.ts` so Node's
built-in `localStorage` does not shadow jsdom. Dropping that flag makes
storage tests talk to the wrong object.

## Search flow

`App` calls `POST /recommend` through `src/api.ts`. A new search aborts the
previous in-flight request. The URL is updated to `?q=`; loading the page with
that param runs the search. Mood chips and the recent-moods rail call the same
handler.

Sort pills reorder the current result list in the browser. They do not call
the API again. `best-match` keeps server order. `highest-rated` and `newest`
sort descending and treat a missing rating or year as `-1`, so those cards
land last. `title-az` uses `localeCompare`. The choice lives in `ResultsGrid`
and resets when a new search starts, because the grid unmounts while the
skeleton is showing.

"More like this" searches
`movies like ${title}, same vibe as "${currentQuery}"`. That string is stored
as a recent mood and written to `?q=` like any other search.

An empty result set or a request error renders `RecoveryPrompt` with six
starter moods (`feel-good comfort`, `smart & talky`, `high-energy thrill`,
`dark & atmospheric`, `nostalgic 90s/00s vibes`, `cozy rainy night`). The
home screen shows a longer chip row (`MoodChips`) plus the recent-moods rail.
Both disappear once a search has started. The popular carousel is hidden then
too. The brand button aborts the request, clears `?q=` with `pushState`, and
returns to the home state.

There is no `popstate` handler. The back button changes the URL without
re-running search.

## Share links

The Share button is shown next to the results heading, including while the
skeleton is up, and hidden when the request errored. If `navigator.share`
exists it is used and the clipboard path is skipped. A user cancel
(`AbortError`) is ignored. Otherwise the button writes the URL to the
clipboard and shows "Copied!" for 2 seconds.

The shared URL replaces the whole query string with `?q=` set to the current
search text. Passed ids, the watchlist, and the sort choice are not in the
link. Opening it runs that query with the receiver's own "don't show hidden"
list.

## Result actions

Cards link the poster to `https://www.themoviedb.org/movie/{tmdb_id}` and
load the image from `https://image.tmdb.org/t/p/w342` plus `poster_path`.
A null path renders "No poster". At most two genre tags are shown. Up to
three provider logos reuse the same region link from the API.

| Action | Toast | Duration |
| --- | --- | --- |
| Pass (hide) | "Hidden" with Undo | 6 seconds |
| Add to watchlist | "Added to watchlist" | 2 seconds |
| Remove from watchlist | "Removed from watchlist" | 2 seconds |
| `localStorage` quota | "Couldn't save — storage full" | 3 seconds |

Undo calls `unpassMovie` for that id. The default toast duration, if a caller
omits one, is 3 seconds. A failed `localStorage.setItem` leaves the previous
value in place and still shows the storage-full toast. The console warning
names `QuotaExceededError` only; any other write error is logged and returns
the same `false`.

My List is a drawer (Escape or the backdrop closes it). Drawer cards can be
unsaved; they do not offer Pass or More like this. Export downloads a file
in the browser: pretty-printed JSON (`moody-watchlist-YYYY-MM-DD.json`,
including `addedAt`) or one text line per title
(`Title (year) - n.n/10`). A missing year, or a missing or zero rating, is
left off that line. Another tab's writes to `moody-watchlist` or
`moody-passed` refresh this tab through the `storage` event.

## Home carousel

`PosterCarousel` lays out four posters per viewport
(`flex-basis: calc((100% - 3 gaps) / 4)`). Arrow clicks and the 4-second
timer both scroll by one full track width, so the page moves four cards at
a time and wraps at either end. Hover pauses the timer. A manual click also
suppresses the next automatic step. `prefers-reduced-motion: reduce` disables
the timer. These cards are display-only: no save, pass, or more-like-this.

## Hidden titles and watchlist

Both live in `localStorage` on this browser. Search sends the query, and
when "don't show hidden" is on, the passed ids as well.

| Key | Contents |
| --- | --- |
| `moody-passed` | JSON array of TMDB ids the user hid |
| `moody-exclude-passed` | `"true"` or `"false"`. Missing or any value other than `"false"` means on |
| `moody-watchlist` | JSON array of movies plus `addedAt` |
| `moody-recent-moods` | Up to 8 queries, newest first, case-insensitive dedupe |
| `movierec:popular-cache` | Last `/popular` payload, treated as stale after 10 minutes |

Passing a card writes the id and hides the card immediately. Toast copy and
durations are in [Result actions](#result-actions). The checkbox labeled
"don't show hidden" appears only after at least one title has been passed.
When it is on (the default), the next search sends those ids as
`exclude_tmdb_ids`. The backend accepts at most 100 ids; a longer list is a
`422` and the search fails. Turning the checkbox off keeps the passed set but
omits it from the request. Passed cards are also filtered out of the grid
even when the server still returns them. Watchlist adds and removes stay in
this browser.

The carousel paints from `movierec:popular-cache` when it is fresh, then
always refetches `GET /popular`. That local cache does not delay a successful
response; staleness of the shelf itself comes from the backend cache described
in the [backend README](../backend/README.md).

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
