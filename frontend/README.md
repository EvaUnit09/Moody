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
that param runs the search.

The mood field is the only textbox and has no accessible name. Its placeholder
rotates every 3.2 seconds, so do not treat the placeholder as a label. Submit
trims the text. A whitespace-only value does not search. The button stays
disabled while the trimmed text is empty or a request is in flight, and its
label is `Thinking...` for that request. The field is disabled at the same time.

"More like this" (accessible name `Find more like this`) is wired only when
the current query is non-empty. It searches
`movies like ${title}, same vibe as "${currentQuery}"`. That sentence is more
than three words, so the backend embeds it as typed and skips expansion. A
successful search still stores it as a recent mood.

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
| `moody-recent-moods` | Up to 8 `{ query, searchedAt }` objects, newest first |
| `movierec:popular-cache` | `{ movies, storedAt }`, ignored after 10 minutes |

`getRecentMoods` returns the query strings. A repeat is matched
case-insensitively and moved to the front. Entries that are not
`{ query: non-empty string, searchedAt: number }` are skipped on read.
A quota failure logs a warning and does not toast; the search result still
shows. `movierec:popular-cache` is a miss when the JSON is not that envelope
or `storedAt` is older than 10 minutes. A failed write is ignored.

### Result cards

`MovieCard` links the poster to `https://www.themoviedb.org/movie/{tmdb_id}`.
Posters use `https://image.tmdb.org/t/p/w342` plus `poster_path`. A null path
renders `No poster`. At most two genres are shown. Year is omitted when it
is null or `0`. Rating is omitted only when it is null, and a present rating
is one decimal (`0` renders as `0.0`). Each provider links to its own
`link`. The API currently sets every provider on a title to that region's
one link. A null `logo_url` shows the provider name instead of an image.

Actions depend on the surface:

| Surface | Heart | Pass | More like this |
| --- | --- | --- | --- |
| Result grid | `Add to watchlist` / `Remove from watchlist` | `Pass on this recommendation` | when the current query is non-empty |
| My List | `Remove from watchlist` only | no | no |
| Home carousel | no | no | no |

Passing writes the id, toasts `Hidden` with `Undo` for 6 seconds, and drops
the card on the next render because the grid filters `passedMovies`. Undo
deletes that id and the card comes back from the current result list,
including when it was the last visible card. Undo does not toast. If the
delete fails, the id stays stored and the card stays hidden. The checkbox
labeled "don't show hidden" appears only after at least one title has been
passed. When it is on (the default), the next search sends those ids as
`exclude_tmdb_ids`. The backend accepts at most 100 ids, so the client sends
`Array.from(passedMovies).slice(-100)`. The set keeps insertion order from
the stored array: a newly passed id is appended, and passing an id that is
already stored leaves it where it is. Non-numeric entries are dropped on
read. Turning the checkbox off keeps the passed set but omits it from the
request. The checkbox state is what the next request uses. The preference
write can fail silently; after a reload the stored value wins. Passed cards
are also filtered out of the grid even when the server still returns them.
If every returned title is already passed, `ResultsGrid` returns null before
the sort pills, and `RecoveryPrompt` stays hidden. That prompt checks
`results.length === 0`, not the filtered list. The `matches for` heading
still shows.

### My List

The header button `Open watchlist` (label `My List`) opens a dialog titled
`My List`. A count badge is shown only when the list is non-empty. Escape
or a backdrop click closes it; the button is `Close watchlist`. The empty
copy is `Your watchlist is empty.` and `Add movies by clicking the heart
icon on any result card.` Export is hidden in that state.

A saved card is prepended (`addedAt` is `Date.now()`), so the newest title
is first. Saving an id that is already present returns success and does not
move it. The stored object must have a numeric `tmdb_id`, a string `title`,
`poster_path` and `year` and `vote_average` each null or the right type, a
string `genres` array, and a numeric `addedAt`. Other objects are skipped
on read. The next successful add or remove rewrites the key from that
filtered list, so invalid entries disappear on the next mutation. A JSON
parse failure reads as an empty list; the next successful add replaces the
stored value.

`Export JSON` downloads `moody-watchlist-YYYY-MM-DD.json` (UTC date), the
pretty-printed stored array. `Export Text` downloads the same date with a
`.txt` suffix, one line per title: `Title (year) - 7.4/10`. Year and rating
are omitted when they are null or `0`.

Any failed watchlist or pass write toasts `Couldn't save — storage full`
for 3 seconds and leaves the previous value in place. That toast is also
what an invalid movie object gets; the copy is not only quota. Adds and
removes that succeed toast `Added to watchlist` or `Removed from watchlist`
for 2 seconds.

Toasts stack in a `Notifications` region. Escape dismisses the newest one
after a 200ms exit. The default duration, if a caller omits it, is 3
seconds. `duration` of `0` does not auto-dismiss. Dismiss is
`Dismiss notification`.

Another tab's `storage` event refreshes `moody-watchlist` and `moody-passed`
only. Recent moods and the exclude checkbox do not listen. Same-tab writes
do not fire `storage`. Returning home re-reads recent moods. The exclude
checkbox is read once, when `App` mounts.

The carousel paints from `movierec:popular-cache` when it is fresh, then
always refetches `GET /popular`. That local cache does not delay a successful
response; staleness of the shelf itself comes from the backend cache described
in the [backend README](../backend/README.md).

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
