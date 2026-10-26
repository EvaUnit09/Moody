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
backend — defaults to `http://localhost:8000`.

CI uses Node 24. Vitest sets `NODE_OPTIONS=--no-experimental-webstorage` in
`vite.config.ts` so Node's built-in `localStorage` does not shadow jsdom.

## Search flow

`App` calls `POST /recommend` through `src/api.ts`. A new search aborts the
previous in-flight request. The URL is updated to `?q=`; loading the page with
that param runs the search. "More like this" searches
`movies like ${title}, same vibe as "${currentQuery}"`.

Sort pills reorder the current result list in the browser (`best-match` keeps
server order, then highest rated, newest, title A–Z). They do not call the API
again. Sort state lives in `ResultsGrid`, which mounts only after a search
finishes without an error. The next search shows the skeleton instead, so the
pills reset to `best-match`. A missing rating or year sorts as `-1` (last for
highest-rated and newest).

`handleSearch` writes `?q=` with `pushState`. That param is read only on the
first mount. There is no `popstate` handler, so Back changes the URL and leaves
the screen where it is. `ShareButton` builds the same URL. It uses
`navigator.share` when that exists (a user cancel is ignored) and otherwise
copies the URL, showing "Copied!" for 2 seconds.

The carousel item width is one quarter of the track (`(100% - 3 gaps) / 4`),
and each auto-step scrolls one track width, so it advances four posters. The
timer is 4 seconds, pauses while the pointer is over the carousel, and does
not start when `prefers-reduced-motion: reduce` matches. An arrow click waits
another 4 seconds before auto-advance. At either end the next step wraps.
If `GET /popular` fails and nothing was painted from `movierec:popular-cache`,
the carousel stays empty; a cache hit is kept.

An empty result list or a request error renders `RecoveryPrompt` with the
copy `Nothing quite matches that. Try one of these instead:`. The API text
is not printed. `api.ts` prefers a string `detail`, then `message`, then
`Request failed with status <code>`. A 422 body whose `detail` is a list
(FastAPI validation) becomes that status sentence. A 429 uses `message`
(`You've made too many requests. Please try again in a minute.`). A 503
uses the string `detail` (`Database busy, try again shortly`). `App` stores
that sentence and, when it is set, hides the `matches for` heading. The
recovery chips still look the same as an empty result set, which keeps the
heading. `AbortError` is ignored. The popular carousel is hidden once a
search has started. The brand button aborts the request and returns to the
home state.

## Preset moods

The recent-moods rail and the preset chips render only on the home screen
(`hasSearched` is false). Starting a search unmounts both. The brand button
clears the query, aborts the request, and shows them again.

`RecentChips` is the rail labeled `Recent`. It is omitted when
`moody-recent-moods` is empty. Each chip searches that saved query. The
`Clear all` button (accessible name `Clear recent searches`) wipes the rail.

`MoodChips` reads `MOOD_GROUPS` in `src/lib/moodGroups.ts` and renders three
sections, in this order. A chip's accessible name is `Search for <mood>
movies`.

| Section | Moods |
| --- | --- |
| Quiet | `slow & melancholic`, `cozy rainy night`, `dark & atmospheric` |
| Warm | `feel-good comfort`, `nothing heavy`, `date night`, `nostalgic 90s/00s vibes` |
| Wired | `high-energy thrill`, `mind-bending`, `smart & talky` |

`RecoveryPrompt` is a different list. It is not `MOOD_GROUPS`. The chips are
`feel-good comfort`, `smart & talky`, `high-energy thrill`, `dark &
atmospheric`, `nostalgic 90s/00s vibes`, and `cozy rainy night`. Each one's
accessible name is `Try <mood> instead`. `slow & melancholic`, `nothing
heavy`, `date night`, and `mind-bending` are home presets only.

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

Passing a card writes the id, shows an Undo toast (6 seconds), and hides the
card immediately. The checkbox labeled "don't show hidden" appears only after
at least one title has been passed. When it is on (the default), the next
search sends those ids as `exclude_tmdb_ids`. The backend accepts at most 100
ids, so the client sends `Array.from(passedMovies).slice(-100)`. The set keeps
insertion order from the stored array: a newly passed id is appended, and
passing an id that is already stored leaves it where it is. Turning the
checkbox off keeps the passed set but omits it from the request. Passed
cards are also filtered out of the grid even when the server still returns
them. If every returned title is already passed, `ResultsGrid` returns null
before the sort pills, and `RecoveryPrompt` stays hidden. That prompt checks
`results.length === 0`, not the filtered list. The `matches for` heading
still shows.

Watchlist adds and removes are local only. Quota failures toast "Couldn't save — storage full" and leave the previous value in place.

The carousel paints from `movierec:popular-cache` when it is fresh, then
always refetches `GET /popular`. That local cache does not delay a successful
response; staleness of the shelf itself comes from the backend cache described
in the [backend README](../backend/README.md).

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
