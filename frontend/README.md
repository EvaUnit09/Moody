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

## Search flow

`App` calls `POST /recommend` through `src/api.ts`. A new search aborts the
previous in-flight request. The URL is updated to `?q=`; loading the page with
that param runs the search. Mood chips and the recent-moods rail call the same
handler. "More like this" searches
`movies like ${title}, same vibe as "${currentQuery}"`.

Sort pills reorder the current result list in the browser (`best-match` keeps
server order, then highest rated, newest, title A–Z). They do not call the API
again.

An empty result set or a request error renders `RecoveryPrompt` with starter
moods. The popular carousel is hidden once a search has started. The brand
button aborts the request and returns to the home state.

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
ids; a longer list is a `422` and the search fails. Turning the checkbox off
keeps the passed set but omits it from the request. Passed cards are also
filtered out of the grid even when the server still returns them.

Watchlist adds and removes are local only. Quota failures toast "Couldn't save — storage full" and leave the previous value in place.

The carousel paints from `movierec:popular-cache` when it is fresh, then
always refetches `GET /popular`. That local cache does not delay a successful
response; staleness of the shelf itself comes from the backend cache described
in the [backend README](../backend/README.md).

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
